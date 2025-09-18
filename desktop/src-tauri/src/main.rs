#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::Serialize;
use serde_json::Value;
use std::env;
use tauri::{
    menu::{MenuBuilder, MenuEvent, MenuItemBuilder},
    tray::TrayIconBuilder,
    AppHandle, Emitter, Manager,
};
use tauri::image::Image;

const DEFAULT_HOST: &str = "http://127.0.0.1:5173";

#[derive(Serialize, Clone)]
struct UiNotification<'a> {
    message: &'a str,
}

#[tauri::command]
fn open_ui(app_handle: AppHandle) -> Result<(), String> {
    if let Some(window) = app_handle.get_webview_window("main") {
        window.show().map_err(|e| e.to_string())?;
        window.set_focus().map_err(|e| e.to_string())?;
        Ok(())
    } else {
        Err("Main window not available".into())
    }
}

#[tauri::command]
fn trigger_ingest(app_handle: AppHandle) -> Result<(), String> {
    let payload = serde_json::json!({ "all": true });
    call_backend("/ingest", "POST", Some(&payload))?;
    app_handle
        .emit(
            "ingest-finished",
            UiNotification {
                message: "Ingest triggered",
            },
        )
        .map_err(|e| e.to_string())?;
    Ok(())
}

fn call_backend(path: &str, method: &str, body: Option<&Value>) -> Result<(), String> {
    let host = env::var("CTXC_HOST").unwrap_or_else(|_| DEFAULT_HOST.to_string());
    let url = format!("{}{}", host.trim_end_matches('/'), path);
    let response = match method {
        "POST" => {
            let request = ureq::post(&url);
            if let Some(payload) = body {
                request.send_json(payload.clone())
            } else {
                request.call()
            }
        }
        "GET" => ureq::get(&url).call(),
        _ => return Err(format!("Unsupported method {method}")),
    };

    response
        .map(|_| ())
        .map_err(|err| format!("Request to {url} failed: {err}"))
}

fn init_tray(app: &AppHandle) -> tauri::Result<()> {
    let open_item = MenuItemBuilder::with_id("open", "Open UI").build(app)?;
    let ingest_item = MenuItemBuilder::with_id("ingest", "Ingest Now").build(app)?;
    let quit_item = MenuItemBuilder::with_id("quit", "Quit").build(app)?;

    let menu = MenuBuilder::new(app)
        .item(&open_item)
        .item(&ingest_item)
        .item(&quit_item)
        .build()?;

    let tray_icon = Image::from_bytes(include_bytes!("../icons/tray.png"))?;

    let tray = TrayIconBuilder::new()
        .icon(tray_icon)
        .menu(&menu)
        .on_menu_event(|app, event: MenuEvent| match event.id().as_ref() {
            "open" => {
                if let Err(err) = open_ui(app.clone()) {
                    eprintln!("Failed to open UI: {err}");
                }
            }
            "ingest" => {
                if let Err(err) = trigger_ingest(app.clone()) {
                    eprintln!("Failed to ingest: {err}");
                }
            }
            "quit" => {
                app.exit(0);
            }
            _ => {}
        })
        .build(app)?;

    app.manage(tray);
    Ok(())
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let handle = app.handle();
            init_tray(&handle)?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![open_ui, trigger_ingest])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
