use crate::config::Config;
use std::collections::HashMap;
use std::time::Instant;
use sysinfo::{MemoryRefreshKind, Pid, ProcessRefreshKind, ProcessesToUpdate, RefreshKind, System};

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum PressureLevel {
    Normal,
    Elevated,
    High,
    Critical,
}

impl std::fmt::Display for PressureLevel {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            PressureLevel::Normal => write!(f, "Normal"),
            PressureLevel::Elevated => write!(f, "Elevated"),
            PressureLevel::High => write!(f, "High"),
            PressureLevel::Critical => write!(f, "Critical"),
        }
    }
}

pub struct ProcessInfo {
    pub pid: Pid,
    pub name: String,
    pub memory_mb: u64,
    pub cpu_percent: f32,
    pub cmd: String,
}

pub struct SystemSnapshot {
    pub total_memory_gb: f64,
    pub used_memory_gb: f64,
    pub free_memory_gb: f64,
    pub total_swap_gb: f64,
    pub used_swap_gb: f64,
    pub top_processes: Vec<ProcessInfo>,
    pub pressure: PressureLevel,
    pub node_count: usize,
    pub node_total_mb: u64,
    pub browser_count: usize,
    pub browser_total_mb: u64,
    pub dev_server_count: usize,
    pub dev_server_total_mb: u64,
}

pub struct Monitor {
    system: System,
    config: Config,
    /// Tracks how long each process has been at ~0% CPU
    idle_tracker: HashMap<Pid, Instant>,
}

impl Monitor {
    pub fn new(config: Config) -> Self {
        let system = System::new_with_specifics(
            RefreshKind::nothing()
                .with_memory(MemoryRefreshKind::everything())
                .with_processes(ProcessRefreshKind::everything()),
        );

        Self {
            system,
            config,
            idle_tracker: HashMap::new(),
        }
    }

    pub fn sample(&mut self) -> SystemSnapshot {
        self.system.refresh_memory();
        self.system.refresh_processes_specifics(
            ProcessesToUpdate::All,
            true,
            ProcessRefreshKind::everything(),
        );

        let total_memory_gb = self.system.total_memory() as f64 / 1_073_741_824.0;
        let used_memory_gb = self.system.used_memory() as f64 / 1_073_741_824.0;
        let free_memory_gb = self.system.available_memory() as f64 / 1_073_741_824.0;
        let total_swap_gb = self.system.total_swap() as f64 / 1_073_741_824.0;
        let used_swap_gb = self.system.used_swap() as f64 / 1_073_741_824.0;

        let mut node_count: usize = 0;
        let mut node_total_mb: u64 = 0;
        let mut browser_count: usize = 0;
        let mut browser_total_mb: u64 = 0;
        let mut dev_server_count: usize = 0;
        let mut dev_server_total_mb: u64 = 0;

        // Collect top processes by memory
        let mut processes: Vec<ProcessInfo> = self
            .system
            .processes()
            .iter()
            .map(|(pid, proc)| {
                let name = proc.name().to_string_lossy().to_string();
                let mem_mb = proc.memory() / 1_048_576;
                let cmd = proc
                    .cmd()
                    .iter()
                    .map(|s| s.to_string_lossy().to_string())
                    .collect::<Vec<_>>()
                    .join(" ");

                // Aggregate stats
                if name.contains("node") || name == "node" {
                    node_count += 1;
                    node_total_mb += mem_mb;
                }
                if name.contains("Brave") || name.contains("Chrome") || name.contains("Firefox") {
                    browser_count += 1;
                    browser_total_mb += mem_mb;
                }
                if !Self::is_browser_process(&name, &cmd)
                    && self
                        .config
                        .safe_kill_patterns
                        .dev_servers
                        .iter()
                        .any(|p| name.contains(p) || cmd.contains(p))
                {
                    dev_server_count += 1;
                    dev_server_total_mb += mem_mb;
                }

                ProcessInfo {
                    pid: *pid,
                    name,
                    memory_mb: mem_mb,
                    cpu_percent: proc.cpu_usage(),
                    cmd,
                }
            })
            .collect();

        processes.sort_by(|a, b| b.memory_mb.cmp(&a.memory_mb));
        processes.truncate(20);

        // Update idle tracker
        let now = Instant::now();
        let current_pids: Vec<Pid> = self.system.processes().keys().copied().collect();

        // Remove dead processes
        self.idle_tracker
            .retain(|pid, _| current_pids.contains(pid));

        // Track idle processes (CPU < 0.5%)
        for (pid, proc) in self.system.processes() {
            if proc.cpu_usage() < 0.5 {
                self.idle_tracker.entry(*pid).or_insert(now);
            } else {
                self.idle_tracker.remove(pid);
            }
        }

        let pressure = self.assess_pressure(free_memory_gb, used_swap_gb);

        SystemSnapshot {
            total_memory_gb,
            used_memory_gb,
            free_memory_gb,
            total_swap_gb,
            used_swap_gb,
            top_processes: processes,
            pressure,
            node_count,
            node_total_mb,
            browser_count,
            browser_total_mb,
            dev_server_count,
            dev_server_total_mb,
        }
    }

    fn assess_pressure(&self, free_gb: f64, swap_gb: f64) -> PressureLevel {
        let t = &self.config.thresholds;

        if free_gb < t.critical_free_gb && swap_gb > t.critical_swap_gb {
            PressureLevel::Critical
        } else if free_gb < t.high_free_gb || swap_gb > t.high_swap_gb {
            PressureLevel::High
        } else if free_gb < t.elevated_free_gb || swap_gb > t.elevated_swap_gb {
            PressureLevel::Elevated
        } else {
            PressureLevel::Normal
        }
    }

    fn is_protected(&self, name: &str) -> bool {
        self.config
            .protected
            .processes
            .iter()
            .any(|p| name.contains(p))
    }

    /// Check if a process is a browser/Chromium-based process by name or command line.
    /// Chromium spawns many helper subprocesses (renderer, GPU, utility, network service)
    /// whose command lines can contain arbitrary strings — we must never match these
    /// as dev servers.
    fn is_browser_process(name: &str, cmd: &str) -> bool {
        const BROWSER_INDICATORS: &[&str] = &[
            "Brave Browser",
            "Google Chrome",
            "Chromium",
            "Firefox",
            "Safari",
            "Arc",
            "Microsoft Edge",
            "Opera",
        ];
        // Check process name
        if BROWSER_INDICATORS.iter().any(|b| name.contains(b)) {
            return true;
        }
        // Chromium helper processes often have names like "Brave Browser Helper (Renderer)"
        // or contain the browser's framework path in cmd
        if name.contains("Helper") && BROWSER_INDICATORS.iter().any(|b| cmd.contains(b)) {
            return true;
        }
        // Catch Chromium framework executables that may have generic names
        const BROWSER_FRAMEWORK_PATHS: &[&str] = &[
            "Brave Browser.app",
            "Google Chrome.app",
            "Chromium.app",
            "Arc.app",
            "Microsoft Edge.app",
            "Opera.app",
        ];
        if BROWSER_FRAMEWORK_PATHS
            .iter()
            .any(|path| cmd.contains(path))
        {
            return true;
        }
        false
    }

    /// Kill a process by PID, returning true if successful
    pub fn kill_process(&self, pid: Pid) -> bool {
        if let Some(proc) = self.system.process(pid) {
            let name = proc.name().to_string_lossy().to_string();
            let cmd = proc
                .cmd()
                .iter()
                .map(|s| s.to_string_lossy().to_string())
                .collect::<Vec<_>>()
                .join(" ");

            if self.is_protected(&name) {
                log::warn!("Refusing to kill protected process: {} (PID {})", name, pid);
                return false;
            }

            // Safety net: never kill browser processes regardless of how we got here
            if Self::is_browser_process(&name, &cmd) {
                log::warn!(
                    "Refusing to kill browser process: {} (PID {})",
                    name,
                    pid
                );
                return false;
            }

            log::info!("Killing process: {} (PID {})", name, pid);
            proc.kill()
        } else {
            false
        }
    }

    /// Find and kill idle dev servers, returning list of (name, pid, memory_mb) killed
    pub fn kill_idle_dev_servers(&mut self) -> Vec<(String, Pid, u64)> {
        let idle_threshold =
            std::time::Duration::from_secs(self.config.auto_kill.idle_dev_server_minutes * 60);
        let now = Instant::now();
        let mut killed = Vec::new();

        let targets: Vec<(Pid, String, u64)> = self
            .system
            .processes()
            .iter()
            .filter_map(|(pid, proc)| {
                let proc_name = proc.name().to_string_lossy().to_string();
                let cmd = proc
                    .cmd()
                    .iter()
                    .map(|s| s.to_string_lossy().to_string())
                    .collect::<Vec<_>>()
                    .join(" ");

                // Skip browser/Chromium processes — their command lines can contain
                // dev server pattern strings as arguments, causing false positives
                if Self::is_browser_process(&proc_name, &cmd) {
                    return None;
                }

                let is_dev_server = self
                    .config
                    .safe_kill_patterns
                    .dev_servers
                    .iter()
                    .any(|pattern| proc_name.contains(pattern) || cmd.contains(pattern));

                if !is_dev_server {
                    return None;
                }

                if self.is_protected(&proc_name) {
                    return None;
                }

                // Check idle time
                if let Some(idle_since) = self.idle_tracker.get(pid) {
                    if now.duration_since(*idle_since) >= idle_threshold {
                        return Some((*pid, proc_name, proc.memory() / 1_048_576));
                    }
                }

                None
            })
            .collect();

        for (pid, name, mem_mb) in targets {
            if self.kill_process(pid) {
                killed.push((name, pid, mem_mb));
            }
        }

        killed
    }

    /// Detect and kill zombie Virtualization VMs (Docker quit but VM still running)
    pub fn kill_zombie_vms(&self) -> Vec<(String, Pid, u64)> {
        if !self.config.auto_kill.zombie_vms {
            return Vec::new();
        }

        // Check if Docker daemon is actually running and has containers
        let docker_active = self.system.processes().values().any(|proc| {
            let name = proc.name().to_string_lossy().to_string();
            name.contains("com.docker.backend") || name.contains("Docker Desktop")
        });

        if docker_active {
            // Docker is running — don't touch the VM
            return Vec::new();
        }

        // Docker is not running, find zombie VMs
        let mut killed = Vec::new();

        let targets: Vec<(Pid, String, u64)> = self
            .system
            .processes()
            .iter()
            .filter_map(|(pid, proc)| {
                let proc_name = proc.name().to_string_lossy().to_string();
                let cmd = proc
                    .cmd()
                    .iter()
                    .map(|s| s.to_string_lossy().to_string())
                    .collect::<Vec<_>>()
                    .join(" ");

                let is_vm = self
                    .config
                    .safe_kill_patterns
                    .zombie_vms
                    .iter()
                    .any(|pattern| proc_name.contains(pattern) || cmd.contains(pattern));

                if is_vm {
                    Some((*pid, proc_name, proc.memory() / 1_048_576))
                } else {
                    None
                }
            })
            .collect();

        for (pid, name, mem_mb) in targets {
            if self.kill_process(pid) {
                log::info!("Killed zombie VM: {} (PID {}, {}MB)", name, pid, mem_mb);
                killed.push((name, pid, mem_mb));
            }
        }

        killed
    }

    /// Generate recommendations based on current snapshot
    pub fn recommendations(&self, snapshot: &SystemSnapshot) -> Vec<String> {
        let mut recs = Vec::new();

        if snapshot.dev_server_count > 0 {
            recs.push(format!(
                "Kill {} dev server(s) to free ~{}MB",
                snapshot.dev_server_count, snapshot.dev_server_total_mb
            ));
        }

        if snapshot.browser_total_mb > 2000 {
            recs.push(format!(
                "Browser using {}MB across {} processes — close tabs or extensions",
                snapshot.browser_total_mb, snapshot.browser_count
            ));
        }

        if snapshot.node_count > 50 {
            recs.push(format!(
                "{} node processes ({}MB) — exit unused Claude Code sessions",
                snapshot.node_count, snapshot.node_total_mb
            ));
        }

        // Check for zombie VMs
        let has_vm = snapshot
            .top_processes
            .iter()
            .any(|p| p.name.contains("Virtualization"));
        let has_docker = snapshot
            .top_processes
            .iter()
            .any(|p| p.name.contains("Docker") || p.name.contains("docker"));
        if has_vm && !has_docker {
            recs.push("Zombie Virtualization VM detected — Docker not running but VM is".to_string());
        }

        if snapshot.used_swap_gb > 10.0 {
            recs.push(format!(
                "Swap at {:.1}GB — system is memory-thrashing",
                snapshot.used_swap_gb
            ));
        }

        recs
    }
}
