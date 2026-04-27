/**
 * Sample TypeScript module for benchmark testing.
 */
import { EventEmitter } from 'events';
import fs from 'fs';
import path from 'path';

const MAX_RETRIES = 3;

export class DataService {
    private cache: Map<string, unknown>;
    private emitter: EventEmitter;

    constructor(private readonly baseUrl: string) {
        this.cache = new Map();
        this.emitter = new EventEmitter();
    }

    async fetch(endpoint: string, retries: number = MAX_RETRIES): Promise<unknown> {
        const cached = this.cache.get(endpoint);
        if (cached) return cached;
        return this.request(endpoint, retries);
    }

    private async request(endpoint: string, retries: number): Promise<unknown> {
        // TODO: add exponential backoff
        const data = await this.load(endpoint);
        this.cache.set(endpoint, data);
        return data;
    }

    private async load(endpoint: string): Promise<unknown> {
        return {};
    }

    clear(): void {
        this.cache.clear();
    }
}

export class ConfigLoader {
    constructor(private readonly configPath: string) {}

    read(): Record<string, unknown> {
        const raw = fs.readFileSync(this.configPath, 'utf-8');
        return this.parse(raw);
    }

    private parse(raw: string): Record<string, unknown> {
        // NOTE: only JSON supported for now
        return JSON.parse(raw);
    }
}

export async function bootstrap(configPath: string): Promise<DataService> {
    const loader = new ConfigLoader(configPath);
    const config = loader.read();
    const baseUrl = (config['baseUrl'] as string) ?? '';
    return new DataService(baseUrl);
}

export function resolveConfigPath(base: string, filename: string): string {
    return path.join(base, filename);
}

const helper = (x: number): number => x * 2;
