import * as vscode from 'vscode';
import * as path from 'path';
import { getCsvHeaders } from '../csv/csvReader';
import { runModelMedic } from '../python/modelmedicRunner';
import { DashboardPanel } from '../webview/dashboard';

export async function analyzeDatasetCommand(context: vscode.ExtensionContext) {
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
        const headers = await getCsvHeaders(csvPath);
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
        DashboardPanel.createOrShow(context.extensionUri);
        DashboardPanel.postMessage({ command: 'setLoading' });

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
                const result = await runModelMedic(csvPath, targetColumn);
                if (token.isCancellationRequested) {
                    return;
                }
                if (result.dataset) {
                    result.dataset.dataset_name = path.basename(csvPath);
                    result.dataset.target = targetColumn;
                }
                DashboardPanel.postMessage({ command: 'renderData', data: result });
                vscode.window.showInformationMessage('ModelMedic analysis completed successfully.');
            } catch (err: any) {
                if (token.isCancellationRequested) {
                    return;
                }
                const errorMsg = err.message || 'Unknown error occurred.';
                vscode.window.showErrorMessage(`ModelMedic analysis failed: ${errorMsg}`);
                DashboardPanel.postMessage({ command: 'error', error: errorMsg });
            }
        });

    } catch (error: any) {
        vscode.window.showErrorMessage(`Failed to read CSV file: ${error.message}`);
    }
}

