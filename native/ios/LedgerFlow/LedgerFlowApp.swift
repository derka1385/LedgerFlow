import SwiftUI
import UIKit
import UserNotifications

@main
struct LedgerFlowApp: App {
    @UIApplicationDelegateAdaptor(ReviewAlerts.self) private var reviewAlerts

    var body: some Scene {
        WindowGroup {
            MobileRoot(reviewAlerts: reviewAlerts)
                .environment(\.locale, Locale(identifier: "en"))
                .preferredColorScheme(.light)
        }
    }
}

@MainActor
final class ReviewAlerts: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate, ObservableObject {
    @Published private(set) var status = UNAuthorizationStatus.notDetermined
    @Published private(set) var openReview: UUID?
    private var publishing = false

    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        UNUserNotificationCenter.current().delegate = self
        return true
    }

    nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification) async -> UNNotificationPresentationOptions {
        notification.request.content.categoryIdentifier == "ledgerflow-review" ? [.banner, .list] : []
    }

    nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse) async {
        guard response.notification.request.content.categoryIdentifier == "ledgerflow-review" else { return }
        await MainActor.run { self.openReview = UUID() }
    }

    func updatePermission() async {
        status = await UNUserNotificationCenter.current().notificationSettings().authorizationStatus
    }

    func enable() async {
        if status == .denied, let settings = URL(string: UIApplication.openSettingsURLString) {
            await UIApplication.shared.open(settings)
            return
        }
        _ = try? await UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge])
        await updatePermission()
    }

    func publish(receipts: [ReceiptRecord], scope: String) async {
        guard !publishing, status == .authorized || status == .provisional else { return }
        publishing = true
        defer { publishing = false }
        let inbox = receipts.filter(\.needsReviewAlert)
        let center = UNUserNotificationCenter.current()
        try? await center.setBadgeCount(inbox.count)

        let key = "ledgerflow.review-alerts.\(scope)"
        let previous = UserDefaults.standard.stringArray(forKey: key) ?? []
        let delivered = Set(previous)
        let unseen = inbox.map { "\($0.id):\($0.updated_at ?? $0.state)" }.filter { !delivered.contains($0) }
        guard !unseen.isEmpty else { return }

        let content = UNMutableNotificationContent()
        content.title = "LedgerFlow · Review needed"
        content.body = unseen.count == 1 ? "A document needs your review." : "\(unseen.count) documents need your review."
        content.categoryIdentifier = "ledgerflow-review"
        let request = UNNotificationRequest(identifier: "ledgerflow-review.\(scope)", content: content, trigger: nil)
        do {
            try await center.add(request)
            UserDefaults.standard.set(Array((previous + unseen).suffix(200)), forKey: key)
        } catch { return }
    }
}
