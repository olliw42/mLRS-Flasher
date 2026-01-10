#!/usr/bin/env node
/**
 * Download embeddable Python for each platform
 * Run with: node scripts/download-python.js [platform]
 * Platform: windows, macos, linux, or all (default)
 */

const https = require('https');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const PYTHON_VERSION = '3.12.12';
const BUILD_DATE = '20251217';

const DOWNLOADS = {
  windows: {
    url: `https://www.python.org/ftp/python/3.12.8/python-3.12.8-embed-amd64.zip`,
    filename: 'python-embed.zip',
    extractCmd: (zipPath, destDir) => {
      // on windows, use powershell to extract
      if (process.platform === 'win32') {
        return `powershell -command "Expand-Archive -Path '${zipPath}' -DestinationPath '${destDir}' -Force"`;
      }
      // on mac/linux, use unzip
      return `unzip -o "${zipPath}" -d "${destDir}"`;
    },
  },
  macos: {
    url: `https://github.com/astral-sh/python-build-standalone/releases/download/${BUILD_DATE}/cpython-${PYTHON_VERSION}+${BUILD_DATE}-x86_64-apple-darwin-install_only.tar.gz`,
    filename: 'python-standalone.tar.gz',
    extractCmd: (tarPath, destDir) => `tar -xzf "${tarPath}" -C "${destDir}"`,
  },
  linux: {
    url: `https://github.com/astral-sh/python-build-standalone/releases/download/${BUILD_DATE}/cpython-${PYTHON_VERSION}+${BUILD_DATE}-x86_64-unknown-linux-gnu-install_only.tar.gz`,
    filename: 'python-standalone.tar.gz',
    extractCmd: (tarPath, destDir) => `tar -xzf "${tarPath}" -C "${destDir}"`,
  },
};

function downloadFile(url, dest) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(dest);

    const request = (url) => {
      https.get(url, (response) => {
        // handle redirects
        if (response.statusCode === 302 || response.statusCode === 301) {
          request(response.headers.location);
          return;
        }

        if (response.statusCode !== 200) {
          reject(new Error(`Failed to download: ${response.statusCode}`));
          return;
        }

        const totalSize = parseInt(response.headers['content-length'], 10);
        let downloadedSize = 0;

        response.on('data', (chunk) => {
          downloadedSize += chunk.length;
          const percent = Math.round((downloadedSize / totalSize) * 100);
          process.stdout.write(`\rDownloading... ${percent}%`);
        });

        response.pipe(file);

        file.on('finish', () => {
          file.close();
          console.log(' Done!');
          resolve();
        });
      }).on('error', (err) => {
        fs.unlink(dest, () => { });
        reject(err);
      });
    };

    request(url);
  });
}

async function downloadPlatform(platform) {
  const config = DOWNLOADS[platform];
  if (!config) {
    console.error(`Unknown platform: ${platform}`);
    return;
  }

  const pythonDir = path.join(__dirname, '..', 'python', platform);
  const tempFile = path.join(__dirname, config.filename);

  // create directory
  fs.mkdirSync(pythonDir, { recursive: true });

  console.log(`\nDownloading Python for ${platform}...`);
  console.log(`URL: ${config.url}`);

  try {
    await downloadFile(config.url, tempFile);

    console.log('Extracting...');
    execSync(config.extractCmd(tempFile, pythonDir), { stdio: 'inherit' });

    // clean up
    fs.unlinkSync(tempFile);

    // for windows, we need to modify python311._pth to enable site-packages
    if (platform === 'windows') {
      const pthFile = path.join(pythonDir, `python${PYTHON_VERSION.replace('.', '').substring(0, 3)}._pth`);
      if (fs.existsSync(pthFile)) {
        let content = fs.readFileSync(pthFile, 'utf8');
        // uncomment import site
        content = content.replace('#import site', 'import site');
        // add Lib/site-packages
        content += '\nLib/site-packages\n';
        fs.writeFileSync(pthFile, content);
        console.log('Updated .pth file to enable site-packages');
      }

      // create Lib/site-packages directory
      fs.mkdirSync(path.join(pythonDir, 'Lib', 'site-packages'), { recursive: true });
    }

    console.log(`Python for ${platform} ready at: ${pythonDir}`);
  } catch (err) {
    console.error(`Failed to setup Python for ${platform}:`, err.message);
  }
}

async function main() {
  const platform = process.argv[2] || 'all';

  if (platform === 'all') {
    for (const p of Object.keys(DOWNLOADS)) {
      await downloadPlatform(p);
    }
  } else {
    await downloadPlatform(platform);
  }
}

main().catch(console.error);
