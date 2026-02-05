/**
 * Typed API client for HyperTrader API.
 * Uses the generated OpenAPI client.
 */

import { setTokenGetter } from '@/lib/api/client';
import {
  getMeApiV1AuthMeGet,
  listTradersApiV1TradersGet,
  createTraderApiV1TradersPost,
  getTraderApiV1TradersTraderIdGet,
  deleteTraderApiV1TradersTraderIdDelete,
  restartTraderApiV1TradersTraderIdRestartPost,
  getTraderStatusApiV1TradersTraderIdStatusGet,
  getTraderLogsApiV1TradersTraderIdLogsGet,
  listUsersApiV1AdminUsersGet,
  listAllTradersApiV1AdminTradersGet,
  getSystemStatsApiV1AdminStatsGet
} from '@/lib/api/generated/sdk.gen';

import type {
  User,
  Trader,
  CreateTraderRequest,
  TraderStatusResponse,
  SystemStats
} from './types';

// Helper to handle response
async function handle<T>(promise: Promise<{ data?: T; error?: unknown }>): Promise<T> {
  const { data, error } = await promise;
  if (error) {
    const err = error as any;
    if (err.detail) throw new Error(JSON.stringify(err.detail));
    throw new Error(JSON.stringify(error));
  }
  return data!;
}

export const api = {
  setPrivyTokenGetter: setTokenGetter,

  // Auth
  async me(): Promise<User> {
    const data = await handle(getMeApiV1AuthMeGet());
    return data as unknown as User;
  },

  // Traders
  async listTraders(): Promise<Trader[]> {
    const data = await handle(listTradersApiV1TradersGet());
    // The backend returns { traders: [], count: 0 }
    // Old api expected Trader[]
    return (data as any).traders as Trader[];
  },

  async getTrader(id: string): Promise<Trader> {
    const data = await handle(getTraderApiV1TradersTraderIdGet({ path: { trader_id: id } }));
    return data as unknown as Trader;
  },

  async createTrader(data: CreateTraderRequest): Promise<Trader> {
    const result = await handle(createTraderApiV1TradersPost({ 
      body: data as any 
    }));
    return result as unknown as Trader;
  },

  async deleteTrader(id: string): Promise<void> {
    await handle(deleteTraderApiV1TradersTraderIdDelete({ path: { trader_id: id } }));
  },

  async restartTrader(id: string): Promise<void> {
    await handle(restartTraderApiV1TradersTraderIdRestartPost({ path: { trader_id: id } }));
  },
  
  // Note: startTrader and stopTrader are not currently exposed in the OpenAPI spec
  async startTrader(_id: string): Promise<void> {
     throw new Error("Start trader not implemented in current API version");
  },
  
  async stopTrader(_id: string): Promise<void> {
     throw new Error("Stop trader not implemented in current API version");
  },

  async getTraderStatus(id: string): Promise<TraderStatusResponse> {
     const data = await handle(getTraderStatusApiV1TradersTraderIdStatusGet({ path: { trader_id: id } }));
     return data as unknown as TraderStatusResponse;
  },

  async getTraderLogs(id: string, lines?: number): Promise<string[]> {
    const data = await handle(getTraderLogsApiV1TradersTraderIdLogsGet({ 
      path: { trader_id: id },
      query: lines ? { tail_lines: lines } : undefined
    }));
    // OpenAPI says logs is a string
    const logs = (data as any).logs as string;
    return logs ? logs.split('\n') : [];
  },

  // Admin
  async adminListUsers(skip = 0, limit = 100): Promise<User[]> {
    const data = await handle(listUsersApiV1AdminUsersGet({ query: { skip, limit } }));
    return data as unknown as User[];
  },

  async adminListTraders(skip = 0, limit = 100): Promise<Trader[]> {
    const data = await handle(listAllTradersApiV1AdminTradersGet({ query: { skip, limit } }));
    return data as unknown as Trader[];
  },

  async adminGetStats(): Promise<SystemStats> {
    const data = await handle(getSystemStatsApiV1AdminStatsGet());
    return data as unknown as SystemStats;
  }
}
