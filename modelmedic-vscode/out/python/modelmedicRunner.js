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
exports.runModelMedic = runModelMedic;
const vscode = __importStar(require("vscode"));
const child_process_1 = require("child_process");
const path = __importStar(require("path"));
/** Timeout for a single ModelMedic run (5 minutes). */
const RUN_TIMEOUT_MS = 5 * 60 * 1000;
/**
 * Try to extract a JSON object/array from a string that may contain
 * non-JSON preamble (Python warnings, deprecation notices, etc.).
 */
function extractJson(raw) {
    // Fast path: the whole string is valid JSON
    const trimmed = raw.trim();
    try {
        return JSON.parse(trimmed);
    }
    catch {
        // ignore – fall through to extraction logic
    }
    // Find the first '{' or '[' and try to parse from there
    for (const opener of ['{', '[']) {
        const idx = trimmed.indexOf(opener);
        if (idx > 0) {
            try {
                return JSON.parse(trimmed.slice(idx));
            }
            catch {
                // keep trying
            }
        }
    }
    throw new Error('No valid JSON found in ModelMedic output.\n' +
        'First 500 chars of output:\n' +
        trimmed.slice(0, 500));
}
async function runModelMedic(csvPath, targetColumn) {
    const config = vscode.workspace.getConfiguration('modelmedic');
    const pythonPath = config.get('pythonPath', 'python');
    const projectPath = config.get('projectPath', 'D:\\ClearML Project\\modelmedic');
    const scriptPath = path.join(projectPath, 'modelmedic.py');
    return new Promise((resolve, reject) => {
        // Use --format json (the non-deprecated flag)
        const args = ['run', csvPath, '--target', targetColumn, '--format', 'json'];
        let child;
        const timer = setTimeout(() => {
            if (child && !child.killed) {
                child.kill();
            }
            reject(new Error(`ModelMedic timed out after ${RUN_TIMEOUT_MS / 1000}s. ` +
                'The dataset may be too large or Python may be stuck.'));
        }, RUN_TIMEOUT_MS);
        child = (0, child_process_1.execFile)(pythonPath, [scriptPath, ...args], { maxBuffer: 1024 * 1024 * 50 }, (error, stdout, stderr) => {
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
            }
            catch (parseError) {
                console.error('Failed to parse ModelMedic output:', stdout.slice(0, 1000));
                if (stderr) {
                    console.error('Stderr was:', stderr);
                }
                reject(new Error('Failed to parse ModelMedic output. ' +
                    parseError.message +
                    (stderr ? `\nStderr: ${stderr.slice(0, 500)}` : '')));
            }
        });
    });
}
//# sourceMappingURL=modelmedicRunner.js.map