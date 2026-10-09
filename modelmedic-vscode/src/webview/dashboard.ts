import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

export class DashboardPanel {
    public static currentPanel: DashboardPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;
    private _disposables: vscode.Disposable[] = [];

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
        this._panel = panel;
        this._extensionUri = extensionUri;

        // Listen for when the panel is disposed
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

        // Update the content based on view changes
        this._panel.webview.onDidReceiveMessage(
            message => {
                switch (message.command) {
                    // Handle messages from webview if needed
                }
            },
            null,
            this._disposables
        );
    }

    public static createOrShow(extensionUri: vscode.Uri) {
        const column = vscode.window.activeTextEditor
            ? vscode.ViewColumn.Beside
            : vscode.ViewColumn.One;

        if (DashboardPanel.currentPanel) {
            DashboardPanel.currentPanel._panel.reveal(column);
            return;
        }

        const panel = vscode.window.createWebviewPanel(
            'modelMedicDashboard',
            'ModelMedic',
            column,
            {
                enableScripts: true,
                localResourceRoots: [
                    // Support both dev (src/) and packaged (out/) paths
                    vscode.Uri.joinPath(extensionUri, 'src', 'webview'),
                    vscode.Uri.joinPath(extensionUri, 'out', 'webview')
                ]
            }
        );

        DashboardPanel.currentPanel = new DashboardPanel(panel, extensionUri);
        DashboardPanel.currentPanel._update();
    }

    public static postMessage(message: any) {
        if (DashboardPanel.currentPanel) {
            DashboardPanel.currentPanel._panel.webview.postMessage(message).then(
                undefined,
                (err) => {
                    // Panel may have been disposed between our check and the
                    // actual postMessage call — swallow the error silently.
                    console.warn('DashboardPanel.postMessage failed (panel likely disposed):', err);
                }
            );
        }
    }

    public dispose() {
        DashboardPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            const x = this._disposables.pop();
            if (x) {
                x.dispose();
            }
        }
    }

    private _update() {
        const webview = this._panel.webview;
        this._panel.webview.html = this._getHtmlForWebview(webview);
    }

    /**
     * Resolve webview assets from src/webview (dev) or out/webview (packaged).
     * Returns the directory that actually contains dashboard.html.
     */
    private _resolveWebviewDir(): string {
        const srcDir = path.join(this._extensionUri.fsPath, 'src', 'webview');
        if (fs.existsSync(path.join(srcDir, 'dashboard.html'))) {
            return srcDir;
        }
        // Fallback to out/webview for packaged extension
        return path.join(this._extensionUri.fsPath, 'out', 'webview');
    }

    private _getHtmlForWebview(webview: vscode.Webview) {
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

function getNonce() {
    let text = '';
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < 32; i++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
}

