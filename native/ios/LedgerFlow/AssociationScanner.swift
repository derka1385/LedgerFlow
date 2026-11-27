import SwiftUI
import VisionKit
import AVFoundation

@MainActor
struct AssociationScanner: UIViewControllerRepresentable {
    let onRead: (String) -> Void
    let onFailure: (String) -> Void
    func makeCoordinator() -> Coordinator { Coordinator(onRead: onRead, onFailure: onFailure) }
    func makeUIViewController(context: Context) -> DataScannerViewController {
        let scanner = DataScannerViewController(recognizedDataTypes: [.barcode(symbologies: [.qr])], qualityLevel: .balanced, recognizesMultipleItems: false, isHighFrameRateTrackingEnabled: false, isPinchToZoomEnabled: true, isGuidanceEnabled: true, isHighlightingEnabled: true)
        scanner.delegate = context.coordinator
        context.coordinator.startTask = Task { @MainActor in
            let allowed = await AVCaptureDevice.requestAccess(for: .video)
            guard !Task.isCancelled else { return }
            guard allowed else { onFailure("Autorisez la caméra dans les réglages pour scanner le code du Mac."); return }
            do { try scanner.startScanning() }
            catch { onFailure("Le scanner n’est pas disponible. Collez le lien d’association à la place.") }
        }
        return scanner
    }
    func updateUIViewController(_ controller: DataScannerViewController, context: Context) {}
    static func dismantleUIViewController(_ controller: DataScannerViewController, coordinator: Coordinator) { coordinator.startTask?.cancel(); controller.stopScanning() }

    @MainActor final class Coordinator: NSObject, DataScannerViewControllerDelegate {
        let onRead: (String) -> Void
        let onFailure: (String) -> Void
        var completed = false
        var startTask: Task<Void, Never>?
        init(onRead: @escaping (String) -> Void, onFailure: @escaping (String) -> Void) { self.onRead = onRead; self.onFailure = onFailure }
        func dataScanner(_ dataScanner: DataScannerViewController, didAdd addedItems: [RecognizedItem], allItems: [RecognizedItem]) {
            guard !completed else { return }
            for item in addedItems {
                if case let .barcode(code) = item, let value = code.payloadStringValue, value.hasPrefix("ledgerflow://connect?") {
                    completed = true; dataScanner.stopScanning(); onRead(value); return
                }
            }
        }
        func dataScanner(_ dataScanner: DataScannerViewController, becameUnavailableWithError error: DataScannerViewController.ScanningUnavailable) {
            guard !completed else { return }
            completed = true; onFailure("La caméra n’est plus disponible. Réessayez ou collez le lien d’association.")
        }
    }
}
