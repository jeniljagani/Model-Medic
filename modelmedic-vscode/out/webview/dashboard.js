"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.DashboardPanel = void 0;
const vscode = __importStar(require("vscode"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
class DashboardPanel {
    static currentPanel;
    _panel;
    _extensionUri;
    _disposables = [];
    constructor(panel, extensionUri) {
        this._panel = panel;
        this._extensionUri = extensionUri;
        // Listen for when the panel is disposed
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
        // Update the content based on view changes
        this._panel.webview.onDidReceiveMessage(message => {
            switch (message.command) {
                // Handle messages from webview if needed
            }
        }, null, this._disposables);
    }
    static createOrShow(extensionUri) {
        const column = vscode.window.activeTextEditor
            ? vscode.ViewColumn.Beside
            : vscode.ViewColumn.One;
        if (DashboardPanel.currentPanel) {
            DashboardPanel.currentPanel._panel.reveal(column);
            return;
        }
        const panel = vscode.window.createWebviewPanel('modelMedicDashboard', 'ModelMedic', column, {
            enableScripts: true,
            localResourceRoots: [
                // Support both dev (src/) and packaged (out/) paths
                vscode.Uri.joinPath(extensionUri, 'src', 'webview'),
                vscode.Uri.joinPath(extensionUri, 'out', 'webview')
            ]
        });
        DashboardPanel.currentPanel = new DashboardPanel(panel, extensionUri);
        DashboardPanel.currentPanel._update();
    }
    static postMessage(message) {
        if (DashboardPanel.currentPanel) {
            DashboardPanel.currentPanel._panel.webview.postMessage(message).then(undefined, (err) => {
                // Panel may have been disposed between our check and the
                // actual postMessage call — swallow the error silently.
                console.warn('DashboardPanel.postMessage failed (panel likely disposed):', err);
            });
        }
    }
    dispose() {
        DashboardPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            const x = this._disposables.pop();
            if (x) {
                x.dispose();
            }
        }
    }
    _update() {
        const webview = this._panel.webview;
        this._panel.webview.html = this._getHtmlForWebview(webview);
    }
    /**
     * Resolve webview assets from src/webview (dev) or out/webview (packaged).
     * Returns the directory that actually contains dashboard.html.
     */
    _resolveWebviewDir() {
        const srcDir = path.join(this._extensionUri.fsPath, 'src', 'webview');
        if (fs.existsSync(path.join(srcDir, 'dashboard.html'))) {
            return srcDir;
        }
        // Fallback to out/webview for packaged extension
        return path.join(this._extensionUri.fsPath, 'out', 'webview');
    }
    _getHtmlForWebview(webview) {
        const webviewDir = this._resolveWebviewDir();
        const htmlPath = path.join(webviewDir, 'dashboard.html');
        let html = fs.readFileSync(htmlPath, 'utf8');
        // Local path to main script run in the webview
        const scriptPathOnDisk = vscode.Uri.file(path.join(webviewDir, 'dashboard.js'));
        const scriptUri = webview.asWebviewUri(scriptPathOnDisk);
        // Local path to css styles
        const stylePathOnDisk = vscode.Uri.file(path.join(webviewDir, 'dashboard.css'));
        const styleUri = webview.asWebviewUri(stylePathOnDisk);
        const nonce = getNonce();
        // Use Content Security Policy
        const csp = `default-src 'none'; img-src 'self' data: https:; style-src ${webview.cspSource}; script-src 'nonce-${nonce}';`;
        // Inject URIs
        html = html.replace('${cssUri}', styleUri.toString());
        html = html.replace('${jsUri}', scriptUri.toString());
        // We could also inject a meta tag for CSP, but simple html string manipulation is fine for now
        // Let's inject CSP into the head
        html = html.replace('<head>', `<head>\n<meta http-equiv="Content-Security-Policy" content="${csp}">`);
        // Add nonce to script
        html = html.replace('<script ', `<script nonce="${nonce}" `);
        return html;
    }
}
exports.DashboardPanel = DashboardPanel;
function getNonce() {
    let text = '';
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < 32; i++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
}
//# sourceMappingURL=dashboard.js.map