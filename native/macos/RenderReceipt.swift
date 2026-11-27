import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

let arguments = CommandLine.arguments
guard arguments.count == 3,
      let document = CGPDFDocument(URL(fileURLWithPath: arguments[1]) as CFURL), !document.isEncrypted else { exit(1) }
guard document.numberOfPages == 1, let page = document.page(at: 1) else { exit(2) }

let box = page.getBoxRect(.cropBox)
let rotated = page.rotationAngle % 180 != 0
let width = rotated ? box.height : box.width
let height = rotated ? box.width : box.height
guard width.isFinite, height.isFinite, width > 0, height > 0 else { exit(1) }
let scale = 2400 / max(width, height)
let pixelsWide = max(1, Int((width * scale).rounded()))
let pixelsHigh = max(1, Int((height * scale).rounded()))
guard let canvas = CGContext(data: nil, width: pixelsWide, height: pixelsHigh, bitsPerComponent: 8, bytesPerRow: 0,
    space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue) else { exit(1) }
let bounds = CGRect(x: 0, y: 0, width: pixelsWide, height: pixelsHigh)
canvas.setFillColor(gray: 1, alpha: 1)
canvas.fill(bounds)
canvas.concatenate(page.getDrawingTransform(.cropBox, rect: bounds, rotate: 0, preserveAspectRatio: true))
canvas.drawPDFPage(page)

guard let image = canvas.makeImage(),
      let destination = CGImageDestinationCreateWithURL(URL(fileURLWithPath: arguments[2]) as CFURL,
        UTType.jpeg.identifier as CFString, 1, nil) else { exit(1) }
CGImageDestinationAddImage(destination, image, [kCGImageDestinationLossyCompressionQuality: 0.91] as CFDictionary)
guard CGImageDestinationFinalize(destination) else { exit(1) }
