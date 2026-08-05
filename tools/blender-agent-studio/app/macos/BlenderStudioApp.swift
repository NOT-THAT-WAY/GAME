import Cocoa
import WebKit

final class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKScriptMessageHandler {
    private var window: NSWindow!
    private var webView: WKWebView!
    private var loading: NSView!
    private var status: NSTextField!
    private var retry: NSButton!
    private var attempts = 0
    private let studioURL = URL(string: "http://127.0.0.1:8778/?desktop=1")!
    private let healthURL = URL(string: "http://127.0.0.1:8778/api/health")!
    private var root: String { Bundle.main.object(forInfoDictionaryKey: "BlenderProjectRoot") as? String ?? FileManager.default.currentDirectoryPath }
    private var compose: String { Bundle.main.object(forInfoDictionaryKey: "StudioComposePath") as? String ?? "" }
    private var defaultBlend: String { Bundle.main.object(forInfoDictionaryKey: "BlenderDefaultBlend") as? String ?? "" }
    private var rootURL: URL { URL(fileURLWithPath: root).standardizedFileURL.resolvingSymlinksInPath() }

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        configureMenu()
        configureWindow()
        NSApp.activate(ignoringOtherApps: true)
        ensureBackend()
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }

    private func configureWindow() {
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .default()
        config.preferences.setValue(true, forKey: "developerExtrasEnabled")
        config.userContentController.add(self, name: "studio")
        webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = self
        webView.translatesAutoresizingMaskIntoConstraints = false
        webView.isHidden = true

        let rootView = NSView()
        rootView.wantsLayer = true
        rootView.layer?.backgroundColor = NSColor(calibratedRed: 0.063, green: 0.067, blue: 0.078, alpha: 1).cgColor
        rootView.addSubview(webView)

        loading = NSView()
        loading.translatesAutoresizingMaskIntoConstraints = false
        rootView.addSubview(loading)
        let mark = NSTextField(labelWithString: "B")
        mark.font = .systemFont(ofSize: 42, weight: .black)
        mark.textColor = NSColor(calibratedRed: 0.949, green: 0.478, blue: 0.145, alpha: 1)
        mark.alignment = .center
        let title = NSTextField(labelWithString: "BLENDER STUDIO")
        title.font = .systemFont(ofSize: 13, weight: .bold)
        title.textColor = .white
        title.alignment = .center
        let spinner = NSProgressIndicator()
        spinner.style = .spinning
        spinner.startAnimation(nil)
        status = NSTextField(labelWithString: "Démarrage du moteur local…")
        status.textColor = NSColor(calibratedWhite: 0.6, alpha: 1)
        status.alignment = .center
        status.maximumNumberOfLines = 3
        retry = NSButton(title: "Réessayer", target: self, action: #selector(retryBackend))
        retry.bezelStyle = .rounded
        retry.isHidden = true
        let stack = NSStackView(views: [mark, title, spinner, status, retry])
        stack.orientation = .vertical
        stack.alignment = .centerX
        stack.spacing = 12
        stack.translatesAutoresizingMaskIntoConstraints = false
        loading.addSubview(stack)
        NSLayoutConstraint.activate([
            webView.leadingAnchor.constraint(equalTo: rootView.leadingAnchor), webView.trailingAnchor.constraint(equalTo: rootView.trailingAnchor), webView.topAnchor.constraint(equalTo: rootView.topAnchor), webView.bottomAnchor.constraint(equalTo: rootView.bottomAnchor),
            loading.leadingAnchor.constraint(equalTo: rootView.leadingAnchor), loading.trailingAnchor.constraint(equalTo: rootView.trailingAnchor), loading.topAnchor.constraint(equalTo: rootView.topAnchor), loading.bottomAnchor.constraint(equalTo: rootView.bottomAnchor),
            stack.centerXAnchor.constraint(equalTo: loading.centerXAnchor), stack.centerYAnchor.constraint(equalTo: loading.centerYAnchor), stack.widthAnchor.constraint(lessThanOrEqualToConstant: 480)
        ])

        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1440, height: 920), styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
        window.title = "Blender Studio"
        window.minSize = NSSize(width: 960, height: 650)
        window.contentView = rootView
        window.center()
        window.setFrameAutosaveName("BlenderAgentStudioMainWindow")
        window.makeKeyAndOrderFront(nil)
    }

    private func configureMenu() {
        let menu = NSMenu()
        let appItem = NSMenuItem(); let appMenu = NSMenu()
        appMenu.addItem(withTitle: "À propos de Blender Studio", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Quitter Blender Studio", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu; menu.addItem(appItem)
        let navItem = NSMenuItem(); navItem.title = "Navigation"; let nav = NSMenu(title: "Navigation")
        let reload = nav.addItem(withTitle: "Actualiser", action: #selector(reloadPage), keyEquivalent: "r"); reload.target = self
        let blender = nav.addItem(withTitle: "Ouvrir le projet Blender", action: #selector(openDefaultBlender), keyEquivalent: "b"); blender.target = self
        let vscode = nav.addItem(withTitle: "Ouvrir dans VS Code", action: #selector(openVSCode), keyEquivalent: "o"); vscode.keyEquivalentModifierMask = [.command, .shift]; vscode.target = self
        navItem.submenu = nav; menu.addItem(navItem)
        let windowItem = NSMenuItem(); windowItem.title = "Fenêtre"; let windowMenu = NSMenu(title: "Fenêtre")
        windowMenu.addItem(withTitle: "Réduire", action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m")
        windowMenu.addItem(withTitle: "Plein écran", action: #selector(NSWindow.toggleFullScreen(_:)), keyEquivalent: "f").keyEquivalentModifierMask = [.command, .control]
        windowItem.submenu = windowMenu; menu.addItem(windowItem)
        NSApp.mainMenu = menu
    }

    @objc private func reloadPage() { webView.reload() }
    @objc private func retryBackend() { attempts = 0; retry.isHidden = true; ensureBackend() }
    @objc private func openDefaultBlender() {
        guard !defaultBlend.isEmpty, let target = containedURL(defaultBlend) else { openBlender(path: nil); return }
        openBlender(path: target.path)
    }
    @objc private func openVSCode() { launch("/usr/bin/open", ["-a", "Visual Studio Code", root]) }

    private func ensureBackend() {
        checkHealth { [weak self] healthy in
            guard let self else { return }
            if healthy { self.showStudio(); return }
            if self.attempts == 0 { self.startCompose() }
            self.attempts += 1
            DispatchQueue.main.async { self.status.stringValue = self.attempts < 12 ? "Docker prépare Blender Studio…" : "Le moteur local ne répond pas." }
            if self.attempts < 12 { DispatchQueue.main.asyncAfter(deadline: .now() + 2) { self.ensureBackend() } }
            else { DispatchQueue.main.async { self.retry.isHidden = false } }
        }
    }
    private func checkHealth(completion: @escaping (Bool) -> Void) {
        var req = URLRequest(url: healthURL); req.timeoutInterval = 1.5
        URLSession.shared.dataTask(with: req) { _, response, _ in completion((response as? HTTPURLResponse)?.statusCode == 200) }.resume()
    }
    private func startCompose() {
        guard !compose.isEmpty else { return }
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            let process = Process(); process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
            process.arguments = ["docker", "compose", "-f", self?.compose ?? "", "up", "--build", "-d"]
            process.currentDirectoryURL = URL(fileURLWithPath: self?.compose ?? "").deletingLastPathComponent()
            var env = ProcessInfo.processInfo.environment; env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"; process.environment = env
            process.standardOutput = Pipe(); process.standardError = process.standardOutput
            try? process.run(); process.waitUntilExit()
        }
    }
    private func showStudio() { DispatchQueue.main.async { self.loading.isHidden = true; self.webView.isHidden = false; self.webView.load(URLRequest(url: self.studioURL, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 15)) } }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard let body = message.body as? [String: Any], let action = body["action"] as? String else { return }
        let raw = body["path"] as? String ?? ""
        let requested = raw.isEmpty ? root : raw
        guard let target = containedURL(requested) else { return }
        switch action {
        case "openBlender": raw.isEmpty ? openDefaultBlender() : openBlender(path: target.path)
        case "reveal": NSWorkspace.shared.activateFileViewerSelecting([target])
        case "openVSCode": openVSCode()
        default: break
        }
    }
    private func containedURL(_ raw: String) -> URL? {
        let candidate = raw.hasPrefix("/") ? URL(fileURLWithPath: raw) : rootURL.appendingPathComponent(raw)
        let target = candidate.standardizedFileURL.resolvingSymlinksInPath()
        let base = rootURL.path
        guard target.path == base || target.path.hasPrefix(base + "/") else { return nil }
        return target
    }
    private func openBlender(path: String?) {
        guard let appURL = NSWorkspace.shared.urlForApplication(withBundleIdentifier: "org.blenderfoundation.blender") ?? (FileManager.default.fileExists(atPath: "/Applications/Blender.app") ? URL(fileURLWithPath: "/Applications/Blender.app") : nil) else { return }
        let config = NSWorkspace.OpenConfiguration(); config.arguments = path.map { [$0] } ?? []; config.activates = true
        NSWorkspace.shared.openApplication(at: appURL, configuration: config) { _, error in if let error { NSLog("Blender launch: \(error)") } }
    }
    private func launch(_ executable: String, _ args: [String]) { let p = Process(); p.executableURL = URL(fileURLWithPath: executable); p.arguments = args; try? p.run() }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
