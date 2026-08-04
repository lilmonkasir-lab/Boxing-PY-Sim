#!/bin/bash
# NexusSec Android APK Builder Script
# Run this script on any computer with Android SDK / Gradle installed.

set -e

echo "=========================================="
echo " Building NexusSec Mobile Pentest APK"
echo "=========================================="

cd "$(dirname "$0")/frontend"

echo "[1/3] Installing frontend dependencies..."
npm install

echo "[2/3] Building Web Production Assets..."
npm run build

echo "[3/3] Building Android APK..."
if [ -f "android/gradlew" ]; then
    cd android
    chmod +x gradlew
    ./gradlew assembleDebug
else
    cd android
    gradle assembleDebug
fi

echo "=========================================="
echo " SUCCESS! APK generated at:"
echo " frontend/android/app/build/outputs/apk/debug/app-debug.apk"
echo "=========================================="
