import * as fs from 'fs';
import * as readline from 'readline';

/**
 * Reads the first line of a CSV file to extract headers.
 * Does not use external libraries.
 */
export async function getCsvHeaders(filePath: string): Promise<string[]> {
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
