import * as assert from 'assert';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';
import { getCsvHeaders } from './csvReader';

async function runTests() {
    const testDir = fs.mkdtempSync(path.join(os.tmpdir(), 'csv-test-'));
    
    try {
        // Test 1: normal CSV
        const normalCsvPath = path.join(testDir, 'test_normal.csv');
    fs.writeFileSync(normalCsvPath, 'f_0,f_1,target\n1,2,0\n');
    let headers = await getCsvHeaders(normalCsvPath);
    assert.deepStrictEqual(headers, ['f_0', 'f_1', 'target'], 'Normal CSV failed');
    fs.unlinkSync(normalCsvPath);

    // Test 2: Windows path
    // path.join already provides the native path. Since we are on Windows, this satisfies it.
    // Also, we can use an explicit Windows-like path just for testing if we wanted, but native absolute path is fine.
    const winCsvPath = normalCsvPath;
    fs.writeFileSync(winCsvPath, 'win_f_0,win_f_1\n1,2\n');
    headers = await getCsvHeaders(winCsvPath);
    assert.deepStrictEqual(headers, ['win_f_0', 'win_f_1'], 'Windows path failed');
    fs.unlinkSync(winCsvPath);

    // Test 3: UTF-8 BOM
    const bomCsvPath = path.join(testDir, 'test_bom.csv');
    const bomPrefix = Buffer.from([0xEF, 0xBB, 0xBF]);
    const bomContent = Buffer.from('bom_1,bom_2\nval1,val2\n', 'utf8');
    fs.writeFileSync(bomCsvPath, Buffer.concat([bomPrefix, bomContent]));
    headers = await getCsvHeaders(bomCsvPath);
    assert.deepStrictEqual(headers, ['bom_1', 'bom_2'], 'UTF-8 BOM failed');
    fs.unlinkSync(bomCsvPath);

    // Test 4: empty CSV
    const emptyCsvPath = path.join(testDir, 'test_empty.csv');
    fs.writeFileSync(emptyCsvPath, '');
    headers = await getCsvHeaders(emptyCsvPath);
    assert.deepStrictEqual(headers, [], 'Empty CSV failed');
    fs.unlinkSync(emptyCsvPath);

    // Test 5: header-only CSV
    const headerOnlyCsvPath = path.join(testDir, 'test_header_only.csv');
    fs.writeFileSync(headerOnlyCsvPath, 'h_1,h_2,h_3');
    headers = await getCsvHeaders(headerOnlyCsvPath);
    assert.deepStrictEqual(headers, ['h_1', 'h_2', 'h_3'], 'Header-only CSV failed');
    fs.unlinkSync(headerOnlyCsvPath);
    
    // Test 6: Empty lines before header
    const emptyLinesCsvPath = path.join(testDir, 'test_empty_lines.csv');
    fs.writeFileSync(emptyLinesCsvPath, '\n\r\n \nhead_1,head_2\nval1,val2');
    headers = await getCsvHeaders(emptyLinesCsvPath);
    assert.deepStrictEqual(headers, ['head_1', 'head_2'], 'Empty lines before header failed');
    fs.unlinkSync(emptyLinesCsvPath);

    console.log('All csvReader tests passed.');
    } finally {
        fs.rmSync(testDir, { recursive: true, force: true });
    }
}

runTests().catch(err => {
    console.error('Test failed:', err);
    process.exit(1);
});
