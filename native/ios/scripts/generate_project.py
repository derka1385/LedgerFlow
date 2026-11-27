"""Create the checked-in Xcode project. No XcodeGen, CocoaPods or external package required."""
from pathlib import Path
import json
import plistlib

root = Path(__file__).resolve().parents[1]
project = root / "LedgerFlow.xcodeproj"
project.mkdir(exist_ok=True)
objects = {}

def add(key, isa, **fields):
    identifier = f"A1000000000000000000{key:04X}"
    objects[identifier] = {"isa": isa, **fields}
    return identifier

main_swift = add(1, "PBXFileReference", lastKnownFileType="sourcecode.swift", path="LedgerFlowApp.swift", sourceTree="<group>")
mobile_swift = add(2, "PBXFileReference", lastKnownFileType="sourcecode.swift", path="MobileRoot.swift", sourceTree="<group>")
workspace_swift = add(96, "PBXFileReference", lastKnownFileType="sourcecode.swift", path="MobileWorkspace.swift", sourceTree="<group>")
welcome_swift = add(97, "PBXFileReference", lastKnownFileType="sourcecode.swift", path="MobileWelcome.swift", sourceTree="<group>")
endpoint_swift = add(3, "PBXFileReference", lastKnownFileType="sourcecode.swift", path="WorkspaceEndpoint.swift", sourceTree="<group>")
association_swift = add(90,"PBXFileReference",lastKnownFileType="sourcecode.swift",path="WorkspaceAssociation.swift",sourceTree="<group>")
scanner_swift = add(91,"PBXFileReference",lastKnownFileType="sourcecode.swift",path="AssociationScanner.swift",sourceTree="<group>")
trust_swift = add(92,"PBXFileReference",lastKnownFileType="sourcecode.swift",path="../../shared/WorkspaceTrust.swift",sourceTree="<group>")
assets = add(4, "PBXFileReference", lastKnownFileType="folder.assetcatalog", path="Assets.xcassets", sourceTree="<group>")
debug_info = add(5, "PBXFileReference", lastKnownFileType="text.plist.xml", path="Info.Debug.plist", sourceTree="<group>")
release_info = add(6, "PBXFileReference", lastKnownFileType="text.plist.xml", path="Info.Release.plist", sourceTree="<group>")
tests_swift = add(7, "PBXFileReference", lastKnownFileType="sourcecode.swift", path="WorkspaceEndpointTests.swift", sourceTree="<group>")
base_config = add(8, "PBXFileReference", lastKnownFileType="text.xcconfig", path="Base.xcconfig", sourceTree="<group>")
debug_config = add(9, "PBXFileReference", lastKnownFileType="text.xcconfig", path="Debug.xcconfig", sourceTree="<group>")
release_config = add(10, "PBXFileReference", lastKnownFileType="text.xcconfig", path="Release.xcconfig", sourceTree="<group>")
app_product = add(11, "PBXFileReference", explicitFileType="wrapper.application", includeInIndex=0, path="LedgerFlow.app", sourceTree="BUILT_PRODUCTS_DIR")
test_product = add(12, "PBXFileReference", explicitFileType="wrapper.cfbundle", includeInIndex=0, path="LedgerFlowTests.xctest", sourceTree="BUILT_PRODUCTS_DIR")
app_files = [add(20+i, "PBXBuildFile", fileRef=f) for i, f in enumerate([main_swift, mobile_swift, endpoint_swift])]
asset_build = add(24, "PBXBuildFile", fileRef=assets)
test_build = add(25, "PBXBuildFile", fileRef=tests_swift)
extra_files = [add(index, "PBXBuildFile", fileRef=ref) for index, ref in zip((93, 94, 95, 98, 99), (association_swift, scanner_swift, trust_swift, workspace_swift, welcome_swift))]
app_sources = add(30, "PBXSourcesBuildPhase", buildActionMask=2147483647, files=app_files+extra_files, runOnlyForDeploymentPostprocessing=0)
app_resources = add(31, "PBXResourcesBuildPhase", buildActionMask=2147483647, files=[asset_build], runOnlyForDeploymentPostprocessing=0)
app_frameworks = add(32, "PBXFrameworksBuildPhase", buildActionMask=2147483647, files=[], runOnlyForDeploymentPostprocessing=0)
test_sources = add(33, "PBXSourcesBuildPhase", buildActionMask=2147483647, files=[test_build], runOnlyForDeploymentPostprocessing=0)
test_frameworks = add(34, "PBXFrameworksBuildPhase", buildActionMask=2147483647, files=[], runOnlyForDeploymentPostprocessing=0)
app_group = add(40, "PBXGroup", children=[main_swift, mobile_swift, workspace_swift, welcome_swift, endpoint_swift, association_swift, scanner_swift, trust_swift, assets, debug_info, release_info], path="LedgerFlow", sourceTree="<group>")
test_group = add(41, "PBXGroup", children=[tests_swift], path="LedgerFlowTests", sourceTree="<group>")
config_group = add(42, "PBXGroup", children=[base_config, debug_config, release_config], path="Config", sourceTree="<group>")
products_group = add(43, "PBXGroup", children=[app_product, test_product], name="Products", sourceTree="<group>")
main_group = add(44, "PBXGroup", children=[app_group, test_group, config_group, products_group], sourceTree="<group>")

project_common = dict(CLANG_ENABLE_MODULES="YES", CLANG_ENABLE_OBJC_ARC="YES", IPHONEOS_DEPLOYMENT_TARGET="17.0", SDKROOT="iphoneos", SWIFT_VERSION="6.0", SWIFT_STRICT_CONCURRENCY="complete", SWIFT_APPROACHABLE_CONCURRENCY="YES", SUPPORTED_PLATFORMS="iphoneos iphonesimulator")
project_debug = add(50, "XCBuildConfiguration", name="Debug", baseConfigurationReference=debug_config, buildSettings={**project_common, "DEBUG_INFORMATION_FORMAT":"dwarf", "SWIFT_OPTIMIZATION_LEVEL":"-Onone", "SWIFT_ACTIVE_COMPILATION_CONDITIONS":"DEBUG $(inherited)", "ENABLE_TESTABILITY":"YES", "ONLY_ACTIVE_ARCH":"YES"})
project_release = add(51, "XCBuildConfiguration", name="Release", baseConfigurationReference=release_config, buildSettings={**project_common, "DEBUG_INFORMATION_FORMAT":"dwarf-with-dsym", "SWIFT_OPTIMIZATION_LEVEL":"-O", "SWIFT_COMPILATION_MODE":"wholemodule", "VALIDATE_PRODUCT":"YES"})
project_configs = add(52, "XCConfigurationList", buildConfigurations=[project_debug, project_release], defaultConfigurationIsVisible=0, defaultConfigurationName="Release")
app_common = dict(ASSETCATALOG_COMPILER_APPICON_NAME="AppIcon", ASSETCATALOG_COMPILER_GLOBAL_ACCENT_COLOR_NAME="BrandAccent", CODE_SIGN_STYLE="Automatic", CURRENT_PROJECT_VERSION="1", GENERATE_INFOPLIST_FILE="NO", INFOPLIST_FILE="LedgerFlow/Info.$(CONFIGURATION).plist", MARKETING_VERSION="0.1.0", PRODUCT_BUNDLE_IDENTIFIER="$(LEDGERFLOW_BUNDLE_IDENTIFIER)", PRODUCT_NAME="$(TARGET_NAME)", SWIFT_DEFAULT_ACTOR_ISOLATION="MainActor", TARGETED_DEVICE_FAMILY="1,2", SUPPORTS_MACCATALYST="NO", SUPPORTS_MAC_DESIGNED_FOR_IPHONE_IPAD="NO", LD_RUNPATH_SEARCH_PATHS="$(inherited) @executable_path/Frameworks")
app_debug = add(53, "XCBuildConfiguration", name="Debug", buildSettings=app_common.copy())
app_release = add(54, "XCBuildConfiguration", name="Release", buildSettings=app_common.copy())
app_configs = add(55, "XCConfigurationList", buildConfigurations=[app_debug, app_release], defaultConfigurationIsVisible=0, defaultConfigurationName="Release")
test_common = dict(BUNDLE_LOADER="$(TEST_HOST)", CODE_SIGN_STYLE="Automatic", GENERATE_INFOPLIST_FILE="YES", PRODUCT_BUNDLE_IDENTIFIER="$(LEDGERFLOW_BUNDLE_IDENTIFIER).tests", PRODUCT_NAME="$(TARGET_NAME)", TARGETED_DEVICE_FAMILY="1,2", TEST_HOST="$(BUILT_PRODUCTS_DIR)/LedgerFlow.app/LedgerFlow", SWIFT_DEFAULT_ACTOR_ISOLATION="MainActor", LD_RUNPATH_SEARCH_PATHS="$(inherited) @executable_path/Frameworks @loader_path/Frameworks")
test_debug = add(56, "XCBuildConfiguration", name="Debug", buildSettings=test_common.copy())
test_release = add(57, "XCBuildConfiguration", name="Release", buildSettings=test_common.copy())
test_configs = add(58, "XCConfigurationList", buildConfigurations=[test_debug, test_release], defaultConfigurationIsVisible=0, defaultConfigurationName="Release")
app_target_id = f"A1000000000000000000{60:04X}"
project_id = f"A1000000000000000000{70:04X}"
proxy = add(61, "PBXContainerItemProxy", containerPortal=project_id, proxyType=1, remoteGlobalIDString=app_target_id, remoteInfo="LedgerFlow")
dependency = add(62, "PBXTargetDependency", target=app_target_id, targetProxy=proxy)
app_target = add(60, "PBXNativeTarget", buildConfigurationList=app_configs, buildPhases=[app_sources, app_frameworks, app_resources], buildRules=[], dependencies=[], name="LedgerFlow", productName="LedgerFlow", productReference=app_product, productType="com.apple.product-type.application")
test_target = add(63, "PBXNativeTarget", buildConfigurationList=test_configs, buildPhases=[test_sources, test_frameworks], buildRules=[], dependencies=[dependency], name="LedgerFlowTests", productName="LedgerFlowTests", productReference=test_product, productType="com.apple.product-type.bundle.unit-test")
add(70, "PBXProject", attributes={"BuildIndependentTargetsInParallel":"YES", "LastUpgradeCheck":"2600", "LastSwiftUpdateCheck":"2600", "TargetAttributes":{app_target:{"CreatedOnToolsVersion":"26.0", "ProvisioningStyle":"Automatic"}, test_target:{"CreatedOnToolsVersion":"26.0", "TestTargetID":app_target}}}, buildConfigurationList=project_configs, compatibilityVersion="Xcode 15.0", developmentRegion="en", hasScannedForEncodings=0, knownRegions=["en", "Base"], mainGroup=main_group, productRefGroup=products_group, projectDirPath="", projectRoot="", targets=[app_target, test_target])

def encode(value, indent=0):
    if isinstance(value, dict):
        return "{\n" + "".join("\t"*(indent+1)+json.dumps(str(k))+" = "+encode(v,indent+1)+";\n" for k,v in value.items()) + "\t"*indent+"}"
    if isinstance(value, list):
        return "(" + ", ".join(encode(v,indent) for v in value) + ("," if value else "") + ")"
    return str(value) if isinstance(value, int) else json.dumps(value)

body = {"archiveVersion":1,"classes":{},"objectVersion":56,"objects":objects,"rootObject":project_id}
(project / "project.pbxproj").write_text("// !$*UTF8*$!\n"+encode(body)+"\n")
schemes = project / "xcshareddata" / "xcschemes"
schemes.mkdir(parents=True, exist_ok=True)
ref = f'<BuildableReference BuildableIdentifier="primary" BlueprintIdentifier="{app_target}" BuildableName="LedgerFlow.app" BlueprintName="LedgerFlow" ReferencedContainer="container:LedgerFlow.xcodeproj" />'
test_ref = f'<BuildableReference BuildableIdentifier="primary" BlueprintIdentifier="{test_target}" BuildableName="LedgerFlowTests.xctest" BlueprintName="LedgerFlowTests" ReferencedContainer="container:LedgerFlow.xcodeproj" />'
(schemes / "LedgerFlow.xcscheme").write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<Scheme LastUpgradeVersion="2600" version="1.7">
 <BuildAction parallelizeBuildables="YES" buildImplicitDependencies="YES"><BuildActionEntries>
  <BuildActionEntry buildForTesting="YES" buildForRunning="YES" buildForProfiling="YES" buildForArchiving="YES" buildForAnalyzing="YES">{ref}</BuildActionEntry>
 </BuildActionEntries></BuildAction>
 <TestAction buildConfiguration="Debug" selectedDebuggerIdentifier="Xcode.DebuggerFoundation.Debugger.LLDB" selectedLauncherIdentifier="Xcode.IDEFoundation.Launcher.LLDB" shouldUseLaunchSchemeArgsEnv="YES"><Testables><TestableReference skipped="NO">{test_ref}</TestableReference></Testables></TestAction>
 <LaunchAction buildConfiguration="Debug" selectedDebuggerIdentifier="Xcode.DebuggerFoundation.Debugger.LLDB" selectedLauncherIdentifier="Xcode.IDEFoundation.Launcher.LLDB" launchStyle="0" useCustomWorkingDirectory="NO" ignoresPersistentStateOnLaunch="NO" debugDocumentVersioning="YES" debugServiceExtension="internal" allowLocationSimulation="NO"><BuildableProductRunnable runnableDebuggingMode="0">{ref}</BuildableProductRunnable></LaunchAction>
 <ProfileAction buildConfiguration="Release" shouldUseLaunchSchemeArgsEnv="YES" useCustomWorkingDirectory="NO" debugDocumentVersioning="YES"><BuildableProductRunnable runnableDebuggingMode="0">{ref}</BuildableProductRunnable></ProfileAction>
 <AnalyzeAction buildConfiguration="Debug" />
 <ArchiveAction buildConfiguration="Release" revealArchiveInOrganizer="YES" />
</Scheme>''')
workspace = project / "project.xcworkspace"
workspace.mkdir(exist_ok=True)
(workspace / "contents.xcworkspacedata").write_text('<?xml version="1.0" encoding="UTF-8"?><Workspace version="1.0"><FileRef location="self:" /></Workspace>')

info = {
    "CFBundleDevelopmentRegion":"$(DEVELOPMENT_LANGUAGE)", "CFBundleDisplayName":"LedgerFlow", "CFBundleExecutable":"$(EXECUTABLE_NAME)",
    "CFBundleIdentifier":"$(PRODUCT_BUNDLE_IDENTIFIER)", "CFBundleInfoDictionaryVersion":"6.0", "CFBundleName":"$(PRODUCT_NAME)",
    "CFBundlePackageType":"APPL", "CFBundleShortVersionString":"$(MARKETING_VERSION)", "CFBundleVersion":"$(CURRENT_PROJECT_VERSION)",
    "LSRequiresIPhoneOS":True, "LedgerFlowOrigin":"$(LEDGERFLOW_ORIGIN)",
    "NSCameraUsageDescription":"Photograph a receipt and submit it to your LedgerFlow workspace.",
    "NSPhotoLibraryUsageDescription":"Choose receipt photos to submit to your LedgerFlow workspace.",
    "NSLocalNetworkUsageDescription":"Connect LedgerFlow to your Mac and sync receipts on the same network.",
    "CFBundleURLTypes":[{"CFBundleURLName":"app.ledgerflow.association","CFBundleURLSchemes":["ledgerflow"]}],
    "UIApplicationSceneManifest":{"UIApplicationSupportsMultipleScenes":False,"UISceneConfigurations":{}},
    "UILaunchScreen":{"UIColorName":"LaunchBackground"},
    "UISupportedInterfaceOrientations":["UIInterfaceOrientationPortrait","UIInterfaceOrientationLandscapeLeft","UIInterfaceOrientationLandscapeRight"],
    "UISupportedInterfaceOrientations~ipad":["UIInterfaceOrientationPortrait","UIInterfaceOrientationPortraitUpsideDown","UIInterfaceOrientationLandscapeLeft","UIInterfaceOrientationLandscapeRight"],
}
for configuration in ("Debug", "Release"):
    values = dict(info)
    if configuration == "Debug":
        values["NSAppTransportSecurity"] = {"NSAllowsLocalNetworking":True}
    with (root / "LedgerFlow" / f"Info.{configuration}.plist").open("wb") as stream:
        plistlib.dump(values, stream)
print(project)
