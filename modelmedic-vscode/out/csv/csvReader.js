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
exports.getCsvHeaders = getCsvHeaders;
const fs = __importStar(require("fs"));
const readline = __importStar(require("readline"));
/**
 * Reads the first line of a CSV file to extract headers.
 * Does not use external libraries.
 */
async function getCsvHeaders(filePath) {
    return new Promise((resolve, reject) => {
        const fileStream = fs.createReadStream(filePath, { encoding: 'utf8' });
        fileStream.on('error', (err) => {
            reject(err);
        });
        const rl = readline.createInterface({
            input: fileStream,
            crlfDelay: Infinity
        });
        let resolved = false;
        rl.on('line', (line) => {
            // Remove UTF-8 BOM if present
            if (line.charCodeAt(0) === 0xFEFF) {
                line = line.slice(1);
            }
            line = line.trim();
            if (line.length === 0) {
                return;
            }
            if (!resolved) {
                resolved = true;
                // Handle basic comma splitting, optionally removing quotes
                const headers = line.split(',').map(header => header.trim().replace(/^"|"$/g, ''));
                resolve(headers);
                rl.close();
                fileStream.destroy();
            }
        });
        rl.on('close', () => {
            if (!resolved) {
                resolved = true;
                resolve([]);
            }
        });
    });
}
//# sourceMappingURL=csvReader.js.map