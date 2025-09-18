#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::Serialize;
use std::env;
use tauri::{AppHandle, CustomMenuItem, Manager, SystemTray, SystemTrayEvent, SystemTrayMenu};

const DEFAULT_HOST: &str = "http://127.0.0.1:5173";

#[derive(Serialize)]
struct UiNotification<'a> {
    message: &'a str,
}

#[tauri::command]
fn open_ui(app_handle: AppHandle) -> Result<(), String> {
    if let Some(window) = app_handle.get_window("main") {
        window.show().map_err(|e| e.to_string())?;
        window.set_focus().map_err(|e| e.to_string())?;
        Ok(())
    } else {
        Err("Main window not available".into())
    }
}

#[tauri::command]
fn trigger_ingest(app_handle: AppHandle) -> Result<(), String> {
    call_backend("/ingest", "POST", serde_json::json!({"all": true}))?;
    app_handle
        .emit_all(
            "ingest-finished",
            UiNotification { message: "Ingest triggered" },
        )
        .map_err(|e| e.to_string())?;
    Ok(())
}

fn call_backend(path: &str, method: &str, body: serde_json::Value) -> Result<(), String> {
    let host = env::var("CTXC_HOST").unwrap_or_else(|_| DEFAULT_HOST.to_string());
    let url = format!("{}{}", host.trim_end_matches('/'), path);
    let response = match method {
        "POST" => ureq::post(&url).send_json(body),
        "GET" => ureq::get(&url).call(),
        _ => return Err(format!("Unsupported method {method}")),
    };
    if let Err(err) = response {
        return Err(format!("Request to {url} failed: {err}"));
    }
    Ok(())
}

fn build_tray() -> SystemTray {
    let open = CustomMenuItem::new("open", "Open UI");
    let ingest = CustomMenuItem::new("ingest", "Ingest Now");
    let quit = CustomMenuItem::new("quit", "Quit");
    let menu = SystemTrayMenu::new().add_item(open).add_item(ingest).add_item(quit);
    SystemTray::new().with_menu(menu)
}

fn main() {
    tauri::Builder::default()
        .system_tray(build_tray())
        .on_system_tray_event(|app, event| match event {
            SystemTrayEvent::MenuItemClick { id, .. } => match id.as_str() {
                "open" => {
                    if let Err(err) = open_ui(app.app_handle()) {
                        eprintln!("Failed to open UI: {err}");
                    }
                }
                "ingest" => {
                    if let Err(err) = trigger_ingest(app.app_handle()) {
                        eprintln!("Failed to ingest: {err}");
                    }
                }
                "quit" => {
                    std::process::exit(0);
                }
                _ => {}
            },
            _ => {}
        })
        .invoke_handler(tauri::generate_handler![open_ui, trigger_ingest])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
