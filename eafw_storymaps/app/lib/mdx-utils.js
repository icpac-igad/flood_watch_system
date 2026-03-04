import fs from 'fs';
import path from 'path';
import matter from 'gray-matter';

const STORIES_DIR = path.join(process.cwd(), 'app', 'content', 'stories');

function getMDXFiles(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter((f) => path.extname(f) === '.mdx');
}

function readMDXFile(filePath) {
  const raw = fs.readFileSync(filePath, 'utf-8');
  return matter(raw);
}

export function getStoryBySlug(slug) {
  const filePath = path.join(STORIES_DIR, `${slug}.mdx`);
  if (!fs.existsSync(filePath)) return null;
  const { content, data } = readMDXFile(filePath);
  return { slug, metadata: data, content };
}

export function getAllStories() {
  const files = getMDXFiles(STORIES_DIR);
  return files.map((file) => {
    const slug = path.basename(file, '.mdx');
    const { data } = readMDXFile(path.join(STORIES_DIR, file));
    return { slug, metadata: data };
  });
}
