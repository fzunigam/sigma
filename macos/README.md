# Sigma macOS App - Xcode Setup Guide

This directory contains the Swift sources for the native **Sigma** macOS application. Follow these instructions to set up the project in Xcode, link the files, and build the application cleanly.

---

## 1. Create Xcode Project Template

1. Open **Xcode** on your Mac.
2. Select **File > New > Project...**
3. Choose **macOS** as the platform and **App** as the template, then click **Next**.
4. Configure the project options:
   * **Product Name**: `Sigma`
   * **Organization Identifier**: `com.sigma`
   * **Interface**: `SwiftUI`
   * **Language**: `Swift`
   * *(Do not check Use Core Data or Include Tests)*
5. Click **Next** and save the project inside the `/Users/fzunigam/dev/personal/sigma/macos/` folder.

---

## 2. Link Swift Sources

1. In the Xcode file navigator (left side), delete the automatically generated `ContentView.swift` and `SigmaApp.swift` (move to Trash).
2. Right-click on the `Sigma` group inside Xcode and select **Add Files to "Sigma"...**
3. Navigate to and select the `Sources/` directory:
   * `/Users/fzunigam/dev/personal/sigma/macos/Sources`
4. Ensure **Copy items if needed** is **unchecked** (so it links the files directly in the repository) and **Create groups** is checked, then click **Add**.

---

## 3. Link SQLite3 System Framework

The application uses the built-in system SQLite library to interact directly with Sigma's database file. No external packages are needed:

1. In Xcode, click on the top-level **Sigma** project node in the file navigator.
2. Select the **Sigma** target in the targets list.
3. Select the **General** tab.
4. Scroll down to the **Frameworks, Libraries, and Embedded Content** section.
5. Click the **`+`** (Plus) button.
6. Search for `libsqlite3.tbd` (or `libsqlite3`), select it, and click **Add**.

---

## 4. Disable App Sandbox (Required for Shared Database Access)

To allow the macOS App to read and write directly to `~/.local/share/sgm/sigma.db` without restriction:

1. With the **Sigma** target still selected, go to the **Signing & Capabilities** tab.
2. Locate the **App Sandbox** capability.
3. Click the **`X`** icon next to "App Sandbox" to remove/disable it completely.
   *(This configures `App Sandbox = NO` in your entitlements).*

---

## 5. Build and Run

1. Press **`Cmd + R`** (or select **Product > Run**) to build and run the application.
2. The Stark Black & White interface will open, sharing data instantly with your CLI tracker!
