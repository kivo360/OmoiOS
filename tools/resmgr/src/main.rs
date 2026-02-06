mod config;
mod monitor;

use config::Config;
use monitor::{Monitor, PressureLevel};
use std::env;
use std::fs::OpenOptions;
use std::io::Write;
use std::time::Duration;
use tokio::time;

fn notify(title: &str, body: &str) {
    match mac_notification_sys::send_notification(title, None, body, None) {
        Ok(_) => {}
        Err(e) => log::warn!("Failed to send notification: {}", e),
    }
}

fn format_snapshot(snapshot: &monitor::SystemSnapshot) -> String {
    let mut lines = Vec::new();
    lines.push(format!(
        "Free: {:.1} GB | Swap: {:.1}/{:.1} GB",
        snapshot.free_memory_gb, snapshot.used_swap_gb, snapshot.total_swap_gb
    ));

    let top3: Vec<String> = snapshot
        .top_processes
        .iter()
        .take(3)
        .map(|p| format!("{} ({}MB)", p.name, p.memory_mb))
        .collect();

    if !top3.is_empty() {
        lines.push(format!("Top: {}", top3.join(", ")));
    }

    lines.join("\n")
}

/// Write a trending data point to CSV
fn write_trending(config: &config::Trending, snapshot: &monitor::SystemSnapshot) {
    if !config.enabled {
        return;
    }

    let path = &config.csv_path;
    let needs_header = !std::path::Path::new(path).exists();

    let file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(path);

    let mut file = match file {
        Ok(f) => f,
        Err(e) => {
            log::warn!("Failed to open trending file {}: {}", path, e);
            return;
        }
    };

    if needs_header {
        let _ = writeln!(
            file,
            "timestamp,pressure,used_gb,free_gb,swap_gb,node_count,node_mb,browser_count,browser_mb,devserver_count,devserver_mb"
        );
    }

    let now = chrono_lite_timestamp();
    let _ = writeln!(
        file,
        "{},{},{:.2},{:.2},{:.2},{},{},{},{},{},{}",
        now,
        snapshot.pressure,
        snapshot.used_memory_gb,
        snapshot.free_memory_gb,
        snapshot.used_swap_gb,
        snapshot.node_count,
        snapshot.node_total_mb,
        snapshot.browser_count,
        snapshot.browser_total_mb,
        snapshot.dev_server_count,
        snapshot.dev_server_total_mb,
    );
}

/// Simple timestamp without pulling in chrono crate
fn chrono_lite_timestamp() -> String {
    use std::process::Command;
    Command::new("date")
        .arg("+%Y-%m-%dT%H:%M:%S")
        .output()
        .ok()
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .map(|s| s.trim().to_string())
        .unwrap_or_else(|| "unknown".to_string())
}

/// One-shot status report — print and exit
fn run_status(config: &Config) {
    let mut monitor = Monitor::new(config.clone());
    // Sample twice with a gap so CPU usage is meaningful
    let _ = monitor.sample();
    std::thread::sleep(Duration::from_millis(500));
    let snapshot = monitor.sample();

    let pressure_icon = match snapshot.pressure {
        PressureLevel::Normal => "OK",
        PressureLevel::Elevated => "!",
        PressureLevel::High => "!!",
        PressureLevel::Critical => "!!!",
    };

    println!("=== resmgr status [{}] ===", pressure_icon);
    println!();
    println!(
        "Memory:  {:.1}/{:.1} GB used | {:.1} GB free",
        snapshot.used_memory_gb, snapshot.total_memory_gb, snapshot.free_memory_gb
    );
    println!(
        "Swap:    {:.1}/{:.1} GB used",
        snapshot.used_swap_gb, snapshot.total_swap_gb
    );
    println!("Pressure: {}", snapshot.pressure);
    println!();

    println!("--- Aggregates ---");
    println!(
        "Node:      {} processes, {}MB",
        snapshot.node_count, snapshot.node_total_mb
    );
    println!(
        "Browser:   {} processes, {}MB",
        snapshot.browser_count, snapshot.browser_total_mb
    );
    println!(
        "DevServer: {} processes, {}MB",
        snapshot.dev_server_count, snapshot.dev_server_total_mb
    );
    println!();

    println!("--- Top 10 by Memory ---");
    for (i, p) in snapshot.top_processes.iter().take(10).enumerate() {
        println!(
            "  {:2}. {:>6}MB  {} (PID {})",
            i + 1,
            p.memory_mb,
            p.name,
            p.pid
        );
    }

    let recs = monitor.recommendations(&snapshot);
    if !recs.is_empty() {
        println!();
        println!("--- Recommendations ---");
        for rec in &recs {
            println!("  * {}", rec);
        }
    }
}

#[tokio::main]
async fn main() {
    env_logger::init();

    let args: Vec<String> = env::args().collect();

    // Handle subcommands
    if args.iter().any(|a| a == "status") {
        let config_path = args
            .windows(2)
            .find(|w| w[0] == "--config")
            .map(|w| w[1].as_str());
        let config = Config::load(config_path);
        run_status(&config);
        return;
    }

    // Parse --config flag
    let config_path = args
        .windows(2)
        .find(|w| w[0] == "--config")
        .map(|w| w[1].as_str());

    let config = Config::load(config_path);
    let poll_interval = Duration::from_secs(config.general.poll_interval_seconds);

    log::info!(
        "resmgr starting — polling every {}s",
        config.general.poll_interval_seconds
    );
    log::info!("Protected processes: {:?}", config.protected.processes);
    log::info!(
        "Thresholds: elevated={:.1}GB free, high={:.1}GB free, critical={:.1}GB free",
        config.thresholds.elevated_free_gb,
        config.thresholds.high_free_gb,
        config.thresholds.critical_free_gb,
    );
    if config.trending.enabled {
        log::info!("Trending CSV: {}", config.trending.csv_path);
    }
    if config.auto_kill.zombie_vms {
        log::info!("Zombie VM detection: enabled");
    }

    let mut monitor = Monitor::new(config.clone());
    let mut prev_level = PressureLevel::Normal;
    let mut last_notify = std::time::Instant::now() - Duration::from_secs(300);
    let mut poll_count: u64 = 0;

    let mut interval = time::interval(poll_interval);

    loop {
        interval.tick().await;
        poll_count += 1;

        let snapshot = monitor.sample();
        let level = snapshot.pressure;

        log::debug!(
            "Memory: {:.1}/{:.1} GB used | Free: {:.1} GB | Swap: {:.1}/{:.1} GB | Pressure: {} | Node: {} ({} MB) | DevServers: {}",
            snapshot.used_memory_gb,
            snapshot.total_memory_gb,
            snapshot.free_memory_gb,
            snapshot.used_swap_gb,
            snapshot.total_swap_gb,
            level,
            snapshot.node_count,
            snapshot.node_total_mb,
            snapshot.dev_server_count,
        );

        // Write trending data
        if poll_count % config.trending.write_every_n_polls == 0 {
            write_trending(&config.trending, &snapshot);
        }

        let now = std::time::Instant::now();
        let notify_cooldown = Duration::from_secs(120);

        match level {
            PressureLevel::Normal => {
                if prev_level != PressureLevel::Normal {
                    log::info!("Memory pressure returned to normal");
                }
            }

            PressureLevel::Elevated => {
                // Kill zombie VMs at elevated+ pressure
                let vm_killed = monitor.kill_zombie_vms();
                if !vm_killed.is_empty() {
                    let freed: u64 = vm_killed.iter().map(|(_, _, mb)| mb).sum();
                    log::info!("Killed zombie VM(s), freed ~{}MB", freed);
                }

                if (level != prev_level
                    || now.duration_since(last_notify) > Duration::from_secs(300))
                    && now.duration_since(last_notify) > notify_cooldown
                {
                    let body = format_snapshot(&snapshot);
                    notify("Memory Pressure: Elevated", &body);
                    last_notify = now;
                    log::info!("Elevated pressure — {}", body.replace('\n', " | "));
                }
            }

            PressureLevel::High => {
                // Kill zombie VMs
                let vm_killed = monitor.kill_zombie_vms();

                // Auto-kill idle dev servers
                let killed = monitor.kill_idle_dev_servers();
                let mut body = format_snapshot(&snapshot);

                let mut total_freed: u64 = 0;
                if !vm_killed.is_empty() {
                    let freed: u64 = vm_killed.iter().map(|(_, _, mb)| mb).sum();
                    total_freed += freed;
                    body.push_str(&format!("\nKilled zombie VM(s), freed ~{}MB", freed));
                }

                if !killed.is_empty() {
                    let freed: u64 = killed.iter().map(|(_, _, mb)| mb).sum();
                    total_freed += freed;
                    let names: Vec<String> = killed
                        .iter()
                        .map(|(name, pid, mb)| format!("{} [{}] ({}MB)", name, pid, mb))
                        .collect();
                    body.push_str(&format!(
                        "\nKilled {} idle dev server(s), freed ~{}MB:\n{}",
                        killed.len(),
                        freed,
                        names.join(", ")
                    ));
                    log::info!("Killed idle dev servers: {:?}", names);
                }

                if total_freed > 0 {
                    log::info!("Total freed: ~{}MB", total_freed);
                }

                if now.duration_since(last_notify) > notify_cooldown {
                    notify("Memory Pressure: High", &body);
                    last_notify = now;
                }
            }

            PressureLevel::Critical => {
                // Kill zombie VMs
                let vm_killed = monitor.kill_zombie_vms();

                // Kill ALL dev servers
                let killed = monitor.kill_idle_dev_servers();
                let mut body = format_snapshot(&snapshot);

                if !vm_killed.is_empty() {
                    let freed: u64 = vm_killed.iter().map(|(_, _, mb)| mb).sum();
                    body.push_str(&format!("\nKilled zombie VM(s), freed ~{}MB", freed));
                }

                if !killed.is_empty() {
                    let freed: u64 = killed.iter().map(|(_, _, mb)| mb).sum();
                    body.push_str(&format!(
                        "\nAuto-killed {} process(es), freed ~{}MB",
                        killed.len(),
                        freed
                    ));
                }

                body.push_str("\nConsider: close browser tabs, quit Docker");

                if now.duration_since(last_notify) > Duration::from_secs(60) {
                    notify("CRITICAL: Memory Pressure", &body);
                    last_notify = now;
                }

                log::warn!("CRITICAL pressure — {}", body.replace('\n', " | "));
            }
        }

        prev_level = level;
    }
}
