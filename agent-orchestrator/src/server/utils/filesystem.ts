import fs from "fs";
import path from "path";

export function ensureDir(dirPath: string): void {
  fs.mkdirSync(dirPath, { recursive: true });
}

export function pathExists(targetPath: string): boolean {
  return fs.existsSync(targetPath);
}

export function readTextSafe(filePath: string): string {
  return fs.readFileSync(filePath, "utf8");
}

export function writeTextSafe(filePath: string, content: string): void {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, content, "utf8");
}
