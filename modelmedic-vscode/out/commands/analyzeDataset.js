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
exports.analyzeDatasetCommand = analyzeDatasetCommand;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const csvReader_1 = require("../csv/csvReader");
const modelmedicRunner_1 = require("../python/modelmedicRunner");
const dashboard_1 = require("../webview/dashboard");
async function analyzeDatasetCommand(context) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showErrorMessage('Please open a CSV file before running ModelMedic.');
        return;
    }
    const document = editor.document;
    if (document.languageId !== 'csv' && !document.fileName.toLowerCase().endsWith('.csv')) {
        vscode.window.showErrorMessage('Please open a CSV file before running ModelMedic.');
        return;
    }
    const csvPath = document.fileName;
    try {
        const headers = await (0, csvReader_1.getCsvHeaders)(csvPath);
        if (headers.length === 0) {
            vscode.window.showErrorMessage('The CSV file appears to be empty or headers could not be read.');
            return;
        }
        const targetColumn = await vscode.window.showQuickPick(headers, {
            placeHolder: 'Select target column'
        });
        if (!targetColumn) {
            // User cancelled
            return;
        }
        // Open Dashboard in loading state
        dashboard_1.DashboardPanel.createOrShow(context.extensionUri);
        dashboard_1.DashboardPanel.postMessage({ command: 'setLoading' });
        // Await the progress task so the promise is tracked by VS Code's
        // lifecycle — prevents "Canceled" unhandled rejections on shutdown.
        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: "ModelMedic",
            cancellable: true
        }, async (progress, token) => {
            progress.report({ message: "Analyzing dataset..." });
            // Respect cancellation
            if (token.isCancellationRequested) {
                return;
            }
            try {
                const result = await (0, modelmedicRunner_1.runModelMedic)(csvPath, targetColumn);
                if (token.isCancellationRequested) {
                    return;
                }
                if (result.dataset) {
                    result.dataset.dataset_name = path.basename(csvPath);
                    result.dataset.target = targetColumn;
                }
                dashboard_1.DashboardPanel.postMessage({ command: 'renderData', data: result });
                vscode.window.showInformationMessage('ModelMedic analysis completed successfully.');
            }
            catch (err) {
                if (token.isCancellationRequested) {
                    return;
                }
                const errorMsg = err.message || 'Unknown error occurred.';
                vscode.window.showErrorMessage(`ModelMedic analysis failed: ${errorMsg}`);
                dashboard_1.DashboardPanel.postMessage({ command: 'error', error: errorMsg });
            }
        });
    }
    catch (error) {
        vscode.window.showErrorMessage(`Failed to read CSV file: ${error.message}`);
    }
}
//# sourceMappingURL=analyzeDataset.js.map