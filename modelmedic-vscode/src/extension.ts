import * as vscode from 'vscode';
import { analyzeDatasetCommand } from './commands/analyzeDataset';

export function activate(context: vscode.ExtensionContext) {
    console.log('ModelMedic extension is now active');

    let analyzeDisposable = vscode.commands.registerCommand('modelmedic.analyzeDataset', () => {
        analyzeDatasetCommand(context);
    });

    context.subscriptions.push(analyzeDisposable);
}

export function deactivate() {}
