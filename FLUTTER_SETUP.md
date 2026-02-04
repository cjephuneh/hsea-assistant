# Flutter Installation Guide for macOS

## Option 1: Manual Installation (Recommended)

1. **Download Flutter SDK:**
   ```bash
   cd ~
   git clone https://github.com/flutter/flutter.git -b stable
   ```

2. **Add Flutter to PATH:**
   Add this line to your `~/.zshrc` file:
   ```bash
   export PATH="$PATH:$HOME/flutter/bin"
   ```

3. **Reload your shell:**
   ```bash
   source ~/.zshrc
   ```

4. **Verify installation:**
   ```bash
   flutter doctor
   ```

## Option 2: Using Homebrew (If Option 1 doesn't work)

```bash
brew install --cask flutter
```

Then add to PATH:
```bash
echo 'export PATH="$PATH:/opt/homebrew/bin/flutter/bin"' >> ~/.zshrc
source ~/.zshrc
```

## After Installation

1. **Run Flutter Doctor:**
   ```bash
   flutter doctor
   ```
   This will check your setup and tell you what's missing.

2. **Install Xcode Command Line Tools (if needed):**
   ```bash
   xcode-select --install
   ```

3. **Accept Android licenses (if developing for Android):**
   ```bash
   flutter doctor --android-licenses
   ```

## Quick Setup for This Project

Once Flutter is installed:

```bash
cd /Users/mac/Documents/code/hsea-assistant/flutter
flutter pub get
flutter doctor
```

## Troubleshooting

- If `flutter` command is not found after installation, make sure you've:
  1. Added Flutter to your PATH
  2. Reloaded your shell (`source ~/.zshrc`)
  3. Restarted your terminal

- For Android development, you'll need Android Studio
- For iOS development, you'll need Xcode (macOS only)
