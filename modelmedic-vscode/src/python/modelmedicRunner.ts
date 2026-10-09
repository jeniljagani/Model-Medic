import * as vscode from 'vscode';
import { execFile, ChildProcess } from 'child_process';
import * as path from 'path';

export interface ModelMedicResult {
    dataset?: any;
    model?: any;
    performance?: any;
    feature_diagnostics?: any;
    findings?: any[];
    recommendations?: any[];
    overall_status?: string;
    plots?: Record<string, string>;
    [key: string]: any;
}

/** Timeout for a single ModelMedic run (5 minutes). */
const RUN_TIMEOUT_MS = 5 * 60 * 1000;

/**
 * Try to extract a JSON object/array from a string that may contain
 * non-JSON preamble (Python warnings, deprecation notices, etc.).
 */
function extractJson(raw: string): any {
    // Fast path: the whole string is valid JSON
    const trimmed = raw.trim();
    try {
        return JSON.parse(trimmed);
    } catch {
        // ignore – fall through to extraction logic
    }

    // Find the first '{' or '[' and try to parse from there
    for (const opener of ['{', '[']) {
        const idx = trimmed.indexOf(opener);
        if (idx > 0) {
            try {
                return JSON.parse(trimmed.slice(idx));
            } catch {
                // keep trying
            }
        }
    }

    throw new Error(
        'No valid JSON found in ModelMedic output.\n' +
        'First 500 chars of output:\n' +
        trimmed.slice(0, 500)
    );
}

export async function runModelMedic(csvPath: string, targetColumn: string): Promise<ModelMedicResult> {
    const config = vscode.workspace.getConfiguration('modelmedic');
    const pythonPath = config.get<string>('pythonPath', 'python');
    const projectPath = config.get<string>('projectPath', 'D:\\ClearML Project\\modelmedic');

    const scriptPath = path.join(projectPath, 'modelmedic.py');

    return new Promise((resolve, reject) => {
        // Use --format json (the non-deprecated flag)
        const args = ['run', csvPath, '--target', targetColumn, '--format', 'json'];

        let child: ChildProcess;

        const timer = setTimeout(() => {
            if (child && !child.killed) {
                child.kill();
            }
            reject(new Error(
                `ModelMedic timed out after ${RUN_TIMEOUT_MS / 1000}s. ` +
                'The dataset may be too large or Python may be stuck.'
            ));
        }, RUN_TIMEOUT_MS);

        child = execFile(
            pythonPath,
            [scriptPath, ...args],
            { maxBuffer: 1024 * 1024 * 50 },
            (error, stdout, stderr) => {
                clearTimeout(timer);

                if (error) {
                    console.error('ModelMedic error:', error);
                    console.error('Stderr:', stderr);

                    // Provide helpful context for common issues
                    const hint = stderr.includes('ModuleNotFoundError')
                        ? ' Make sure all Python dependencies are installed (pip install -r requirements.txt).'
                        : stderr.includes('FileNotFoundError')
                        ? ` Verify the dataset path exists: ${csvPath}`
                        : '';

                    return reject(new Error((stderr || error.message) + hint));
                }

                try {
                    const result = extractJson(stdout);
                    resolve(result);
                } catch (parseError) {
                    console.error('Failed to parse ModelMedic output:', stdout.slice(0, 1000));
                    if (stderr) {
                        console.error('Stderr was:', stderr);
                    }
                    reject(new Error(
                        'Failed to parse ModelMedic output. ' +
                        (parseError as Error).message +
                        (stderr ? `\nStderr: ${stderr.slice(0, 500)}` : '')
                    ));
                }
            }
        );
    });
}
