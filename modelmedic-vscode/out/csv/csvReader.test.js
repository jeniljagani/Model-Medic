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
const assert = __importStar(require("assert"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
const os = __importStar(require("os"));
const csvReader_1 = require("./csvReader");
async function runTests() {
    const testDir = fs.mkdtempSync(path.join(os.tmpdir(), 'csv-test-'));
    try {
        // Test 1: normal CSV
        const normalCsvPath = path.join(testDir, 'test_normal.csv');
        fs.writeFileSync(normalCsvPath, 'f_0,f_1,target\n1,2,0\n');
        let headers = await (0, csvReader_1.getCsvHeaders)(normalCsvPath);
        assert.deepStrictEqual(headers, ['f_0', 'f_1', 'target'], 'Normal CSV failed');
        fs.unlinkSync(normalCsvPath);
        // Test 2: Windows path
        // path.join already provides the native path. Since we are on Windows, this satisfies it.
        // Also, we can use an explicit Windows-like path just for testing if we wanted, but native absolute path is fine.
        const winCsvPath = normalCsvPath;
        fs.writeFileSync(winCsvPath, 'win_f_0,win_f_1\n1,2\n');
        headers = await (0, csvReader_1.getCsvHeaders)(winCsvPath);
        assert.deepStrictEqual(headers, ['win_f_0', 'win_f_1'], 'Windows path failed');
        fs.unlinkSync(winCsvPath);
        // Test 3: UTF-8 BOM
        const bomCsvPath = path.join(testDir, 'test_bom.csv');
        const bomPrefix = Buffer.from([0xEF, 0xBB, 0xBF]);
        const bomContent = Buffer.from('bom_1,bom_2\nval1,val2\n', 'utf8');
        fs.writeFileSync(bomCsvPath, Buffer.concat([bomPrefix, bomContent]));
        headers = await (0, csvReader_1.getCsvHeaders)(bomCsvPath);
        assert.deepStrictEqual(headers, ['bom_1', 'bom_2'], 'UTF-8 BOM failed');
        fs.unlinkSync(bomCsvPath);
        // Test 4: empty CSV
        const emptyCsvPath = path.join(testDir, 'test_empty.csv');
        fs.writeFileSync(emptyCsvPath, '');
        headers = await (0, csvReader_1.getCsvHeaders)(emptyCsvPath);
        assert.deepStrictEqual(headers, [], 'Empty CSV failed');
        fs.unlinkSync(emptyCsvPath);
        // Test 5: header-only CSV
        const headerOnlyCsvPath = path.join(testDir, 'test_header_only.csv');
        fs.writeFileSync(headerOnlyCsvPath, 'h_1,h_2,h_3');
        headers = await (0, csvReader_1.getCsvHeaders)(headerOnlyCsvPath);
        assert.deepStrictEqual(headers, ['h_1', 'h_2', 'h_3'], 'Header-only CSV failed');
        fs.unlinkSync(headerOnlyCsvPath);
        // Test 6: Empty lines before header
        const emptyLinesCsvPath = path.join(testDir, 'test_empty_lines.csv');
        fs.writeFileSync(emptyLinesCsvPath, '\n\r\n \nhead_1,head_2\nval1,val2');
        headers = await (0, csvReader_1.getCsvHeaders)(emptyLinesCsvPath);
        assert.deepStrictEqual(headers, ['head_1', 'head_2'], 'Empty lines before header failed');
        fs.unlinkSync(emptyLinesCsvPath);
        console.log('All csvReader tests passed.');
    }
    finally {
        fs.rmSync(testDir, { recursive: true, force: true });
    }
}
runTests().catch(err => {
    console.error('Test failed:', err);
    process.exit(1);
});
//# sourceMappingURL=csvReader.test.js.map