# LedgerFlow for iPhone

Open `LedgerFlow.xcodeproj` in Xcode and run the LedgerFlow scheme on an iPhone. The app targets iOS 17 and uses SwiftUI and VisionKit. Its interface is in English.

## Connect and scan

1. On the Mac, open LedgerFlow and choose **Scan with iPhone** to generate a pairing code. Choose full workspace access to see all permitted workbooks and share the existing conversation.
2. On iPhone, tap **Connect to your Mac** and scan the code. Keep both devices on the same Wi-Fi. The phone verifies the Mac’s certificate against the fingerprint in the pairing code.
3. Use **Workbooks** to see linked Excel files and share the latest version. Use **Scan** to capture a document or import a photo, then choose a workbook or assign it later in **History**. Each scanned page is queued as a separate receipt.
4. Use **Agent** to ask about the connected workspace. The Mac’s existing model setup and permissions apply to the conversation.

**Create an account or sign in** offers a local iPhone profile for scanning before pairing, and invitation sign-in for an existing HTTPS workspace. If you previously paired with an older LedgerFlow build, scan a new code to establish the native session. The previous address can serve as a sign-in hint.

## When the Mac is unavailable

The phone shows whether it can reach the Mac. If the Mac sleeps, leaves the network or quits LedgerFlow, you can still scan and read the last synced workbook, receipt and chat lists. The pending count reflects the actual local queue. Receipts assigned to the same authorized workspace retry when the app is active and the workspace becomes reachable. Receipts captured with **Choose later** need a workbook before they can send. If the Mac changes address after a restart, generate a fresh QR code.

The cache and queued images use iOS file protection and are excluded from backups. Remote sync while the Mac is off requires a hosted workspace. The local profile and queue currently live on this iPhone.

## Build and verify

The simulator supports photo import and pairing-link exchange. The physical device is required to verify the camera and QR scanning. The project’s portable checks cover URL scope, and the hosted Swift tests also cover restoring queued photos after launch.

```sh
DEVELOPER_DIR=/Users/petrinolann/Downloads/Xcode-beta.app/Contents/Developer \
  xcodebuild -project native/ios/LedgerFlow.xcodeproj -scheme LedgerFlow \
  -configuration Debug -destination 'platform=iOS Simulator,name=iPhone 17' \
  -derivedDataPath native/ios/build/mobile-app CODE_SIGNING_ALLOWED=NO test
```

The paper receipt icon can be regenerated with `.venv/bin/python native/ios/scripts/generate_assets.py`. The Xcode project already includes the generated assets.
