# LedgerFlow for iPhone

Open `LedgerFlow.xcodeproj` in Xcode and run the LedgerFlow scheme on an iPhone. The app targets iOS 17 and uses SwiftUI and VisionKit. Its interface is in English.

## Connect and scan

1. On the Mac, open LedgerFlow and choose **Show pairing code** in the final setup step or **Connect iPhone** under **Account & settings**. The code links the complete workspace.
2. On iPhone, tap **Connect to your Mac** and scan the code. Keep both devices on the same Wi-Fi. The phone verifies the Mac’s certificate against the fingerprint in the pairing code.
3. Use **Workbooks** to see linked Excel files and share the latest version. Use **Scan** to capture a document or import a photo, then choose a workbook or assign it later in **History**. Each scanned page is queued as a separate receipt.
4. Use **Agent** to ask about the connected workspace. The Mac’s existing model setup and permissions apply to the conversation.

## Orvect account

**Create an account or sign in** uses Orvect’s Firebase Authentication project for email sign-in, signup, verification and password reset. The phone reads the account profile directly from Firebase and stores the refresh token in the iOS Keychain. The password is never saved in LedgerFlow. The Mac QR grants access to its LedgerFlow workspace. Offline capture and invited HTTPS workspaces remain available from the same sheet.

To enable **Continue with Google**, register the LedgerFlow iOS bundle in Orvect’s Firebase project and obtain its public iOS client ID and reversed URL scheme. Add those values to the ignored local file `Config/Orvect.local.xcconfig`, then rebuild. Use `CLIENT_ID` and `REVERSED_CLIENT_ID` from the LedgerFlow iOS configuration.

```xcconfig
LEDGERFLOW_GOOGLE_CLIENT_ID = <CLIENT_ID>
LEDGERFLOW_GOOGLE_CALLBACK_SCHEME = <REVERSED_CLIENT_ID>
```

## Review alerts

In **History**, tap **Enable review alerts** and allow notifications in iOS. LedgerFlow schedules a local alert when an active sync detects a new document that needs your review. The notification hides supplier and payment details and opens **History → To check**. Newly flagged documents on the Mac appear at the next iPhone sync. Remote alerts while the phone app is closed require APNs.

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
