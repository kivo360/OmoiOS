use serde::Deserialize;
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Deserialize, Clone)]
pub struct Config {
    #[serde(default = "default_general")]
    pub general: General,
    #[serde(default)]
    pub thresholds: Thresholds,
    #[serde(default)]
    pub auto_kill: AutoKill,
    #[serde(default)]
    pub protected: Protected,
    #[serde(default)]
    pub safe_kill_patterns: SafeKillPatterns,
    #[serde(default)]
    pub trending: Trending,
}

#[derive(Debug, Deserialize, Clone)]
pub struct General {
    #[serde(default = "default_poll_interval")]
    pub poll_interval_seconds: u64,
    #[serde(default = "default_log_level")]
    pub log_level: String,
}

#[derive(Debug, Deserialize, Clone)]
pub struct Thresholds {
    #[serde(default = "default_elevated_free")]
    pub elevated_free_gb: f64,
    #[serde(default = "default_elevated_swap")]
    pub elevated_swap_gb: f64,
    #[serde(default = "default_high_free")]
    pub high_free_gb: f64,
    #[serde(default = "default_high_swap")]
    pub high_swap_gb: f64,
    #[serde(default = "default_critical_free")]
    pub critical_free_gb: f64,
    #[serde(default = "default_critical_swap")]
    pub critical_swap_gb: f64,
}

#[derive(Debug, Deserialize, Clone)]
pub struct AutoKill {
    #[serde(default = "default_idle_minutes")]
    pub idle_dev_server_minutes: u64,
    #[serde(default = "default_true")]
    pub orphan_node_always: bool,
    #[serde(default = "default_true")]
    pub zombie_vms: bool,
}

#[derive(Debug, Deserialize, Clone)]
pub struct Protected {
    #[serde(default = "default_protected_processes")]
    pub processes: Vec<String>,
}

#[derive(Debug, Deserialize, Clone)]
pub struct SafeKillPatterns {
    #[serde(default = "default_dev_servers")]
    pub dev_servers: Vec<String>,
    #[serde(default = "default_orphans")]
    pub orphans: Vec<String>,
    #[serde(default = "default_zombie_vm_patterns")]
    pub zombie_vms: Vec<String>,
}

#[derive(Debug, Deserialize, Clone)]
pub struct Trending {
    #[serde(default = "default_true")]
    pub enabled: bool,
    #[serde(default = "default_trending_path")]
    pub csv_path: String,
    #[serde(default = "default_trending_interval")]
    pub write_every_n_polls: u64,
}

// Defaults
fn default_general() -> General {
    General {
        poll_interval_seconds: 30,
        log_level: "info".to_string(),
    }
}

fn default_poll_interval() -> u64 {
    30
}
fn default_log_level() -> String {
    "info".to_string()
}
fn default_elevated_free() -> f64 {
    2.0
}
fn default_elevated_swap() -> f64 {
    15.0
}
fn default_high_free() -> f64 {
    1.0
}
fn default_high_swap() -> f64 {
    25.0
}
fn default_critical_free() -> f64 {
    0.5
}
fn default_critical_swap() -> f64 {
    30.0
}
fn default_idle_minutes() -> u64 {
    10
}
fn default_true() -> bool {
    true
}
fn default_trending_path() -> String {
    "/tmp/resmgr_trending.csv".to_string()
}
fn default_trending_interval() -> u64 {
    2 // Write every 2 polls = every 60s at default 30s interval
}

fn default_protected_processes() -> Vec<String> {
    vec![
        "VoiceInk".to_string(),
        "Wispr Flow".to_string(),
        "Raycast".to_string(),
        "Rectangle Pro".to_string(),
        "WindowServer".to_string(),
        "Finder".to_string(),
        "Dock".to_string(),
        "Bartender".to_string(),
        "loginwindow".to_string(),
        "NordVPN".to_string(),
    ]
}

fn default_dev_servers() -> Vec<String> {
    vec![
        "next-server".to_string(),
        "next dev".to_string(),
        "vite".to_string(),
        "webpack-dev-server".to_string(),
    ]
}

fn default_orphans() -> Vec<String> {
    vec!["node".to_string()]
}

fn default_zombie_vm_patterns() -> Vec<String> {
    vec!["com.apple.Virtualization.VirtualMachine".to_string()]
}

impl Default for General {
    fn default() -> Self {
        default_general()
    }
}

impl Default for Thresholds {
    fn default() -> Self {
        Self {
            elevated_free_gb: default_elevated_free(),
            elevated_swap_gb: default_elevated_swap(),
            high_free_gb: default_high_free(),
            high_swap_gb: default_high_swap(),
            critical_free_gb: default_critical_free(),
            critical_swap_gb: default_critical_swap(),
        }
    }
}

impl Default for AutoKill {
    fn default() -> Self {
        Self {
            idle_dev_server_minutes: default_idle_minutes(),
            orphan_node_always: true,
            zombie_vms: true,
        }
    }
}

impl Default for Protected {
    fn default() -> Self {
        Self {
            processes: default_protected_processes(),
        }
    }
}

impl Default for SafeKillPatterns {
    fn default() -> Self {
        Self {
            dev_servers: default_dev_servers(),
            orphans: default_orphans(),
            zombie_vms: default_zombie_vm_patterns(),
        }
    }
}

impl Default for Trending {
    fn default() -> Self {
        Self {
            enabled: true,
            csv_path: default_trending_path(),
            write_every_n_polls: default_trending_interval(),
        }
    }
}

impl Default for Config {
    fn default() -> Self {
        Self {
            general: General::default(),
            thresholds: Thresholds::default(),
            auto_kill: AutoKill::default(),
            protected: Protected::default(),
            safe_kill_patterns: SafeKillPatterns::default(),
            trending: Trending::default(),
        }
    }
}

impl Config {
    pub fn load(path: Option<&str>) -> Self {
        let config_path = match path {
            Some(p) => PathBuf::from(p),
            None => dirs::config_dir()
                .unwrap_or_else(|| PathBuf::from("~/.config"))
                .join("resmgr")
                .join("config.toml"),
        };

        if config_path.exists() {
            match fs::read_to_string(&config_path) {
                Ok(contents) => match toml::from_str(&contents) {
                    Ok(config) => {
                        log::info!("Loaded config from {}", config_path.display());
                        return config;
                    }
                    Err(e) => {
                        log::warn!("Failed to parse config: {}. Using defaults.", e);
                    }
                },
                Err(e) => {
                    log::warn!("Failed to read config: {}. Using defaults.", e);
                }
            }
        } else {
            log::info!(
                "No config at {}. Using defaults.",
                config_path.display()
            );
        }

        Config::default()
    }
}
