// custom_mmdc.js
const puppeteer = require('puppeteer');
const mmdc = require('@mermaid-js/mermaid-cli');

// Launch Puppeteer with no sandbox
puppeteer.launch({
    args: ['--no-sandbox', '--disable-setuid-sandbox']
}).then(browser => {
    mmdc.runCLI();  // Run mermaid-cli command within configured puppeteer
    browser.close();
}).catch(error => {
    console.error("Error launching Puppeteer with Mermaid CLI:", error);
    process.exit(1);
});