declare module "sql.js" {
  export interface SqlJsDatabase {
    run(sql: string, params?: Array<string | number | null>): void;
    exec(sql: string): unknown[];
    prepare(sql: string): {
      bind(params?: Array<string | number | null>): void;
      step(): boolean;
      getAsObject(): Record<string, unknown>;
      free(): void;
    };
    export(): Uint8Array;
    close(): void;
  }

  export interface SqlJsStatic {
    Database: new (data?: Uint8Array | Buffer) => SqlJsDatabase;
  }

  export type Database = SqlJsDatabase;

  export default function initSqlJs(options?: {
    locateFile?: (file: string) => string;
  }): Promise<SqlJsStatic>;
}
