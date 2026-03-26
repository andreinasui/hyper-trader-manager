/**
 * Tests for TypeScript type definitions.
 * 
 * Validates that types are correctly structured and can be used
 * to build valid request/response objects.
 */

import { describe, it, expect } from 'vitest';
import type {
  CreateTraderRequest,
  Trader,
  TraderStatus,
  ExchangeType,
  NetworkType,
  ValidationError,
  ApiError,
  User,
  LoginRequest,
  LoginResponse,
} from '../types';

describe('Type Validation', () => {
  describe('CreateTraderRequest', () => {
    it('should accept valid trader creation request', () => {
      const validRequest: CreateTraderRequest = {
        wallet_address: '0x1234567890123456789012345678901234567890',
        private_key: '0x1234567890123456789012345678901234567890123456789012345678901234',
        config: {
          name: 'Test Trader',
          exchange: 'hyperliquid',
          self_account: {
            address: '0x1234567890123456789012345678901234567890',
            base_url: 'testnet',
          },
          copy_account: {
            address: '0xabcdefabcdefabcdefabcdefabcdefabcdefabcd',
            base_url: 'testnet',
          },
        },
      };

      expect(validRequest.wallet_address).toBe('0x1234567890123456789012345678901234567890');
      expect(validRequest.config.name).toBe('Test Trader');
      expect(validRequest.config.exchange).toBe('hyperliquid');
      expect(validRequest.config.self_account.base_url).toBe('testnet');
      expect(validRequest.config.copy_account.base_url).toBe('testnet');
    });

    it('should accept mainnet network type', () => {
      const request: CreateTraderRequest = {
        wallet_address: '0x1234567890123456789012345678901234567890',
        private_key: '0xabc',
        config: {
          name: 'Mainnet Trader',
          exchange: 'hyperliquid',
          self_account: {
            address: '0x1234567890123456789012345678901234567890',
            base_url: 'mainnet',
          },
          copy_account: {
            address: '0xabcdefabcdefabcdefabcdefabcdefabcdefabcd',
            base_url: 'mainnet',
          },
        },
      };

      expect(request.config.self_account.base_url).toBe('mainnet');
      expect(request.config.copy_account.base_url).toBe('mainnet');
    });

    it('should have correct structure for hyperliquid exchange', () => {
      const exchange: ExchangeType = 'hyperliquid';
      
      const request: CreateTraderRequest = {
        wallet_address: '0x123',
        private_key: '0xabc',
        config: {
          name: 'Test',
          exchange: exchange,
          self_account: {
            address: '0x123',
            base_url: 'testnet',
          },
          copy_account: {
            address: '0x456',
            base_url: 'testnet',
          },
        },
      };

      expect(request.config.exchange).toBe('hyperliquid');
    });
  });

  describe('Trader', () => {
    it('should accept valid trader response structure', () => {
      const validTrader: Trader = {
        id: 'uuid-here',
        user_id: 'user-uuid',
        wallet_address: '0x1234567890123456789012345678901234567890',
        runtime_name: 'trader-12345678',
        status: 'running',
        image_tag: 'latest',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        latest_config: { name: 'Test' },
      };

      expect(validTrader.id).toBe('uuid-here');
      expect(validTrader.status).toBe('running');
      expect(validTrader.runtime_name).toBe('trader-12345678');
    });

    it('should accept all valid trader statuses', () => {
      const statuses: TraderStatus[] = ['pending', 'running', 'stopped', 'error'];
      
      statuses.forEach((status) => {
        const trader: Trader = {
          id: 'id',
          user_id: 'user-id',
          wallet_address: '0x123',
          runtime_name: 'trader-123',
          status: status,
          image_tag: 'latest',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        };

        expect(trader.status).toBe(status);
      });
    });

    it('should accept optional latest_config', () => {
      const traderWithoutConfig: Trader = {
        id: 'id',
        user_id: 'user-id',
        wallet_address: '0x123',
        runtime_name: 'trader-123',
        status: 'pending',
        image_tag: 'latest',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };

      const traderWithConfig: Trader = {
        ...traderWithoutConfig,
        latest_config: {
          name: 'My Trader',
          exchange: 'hyperliquid',
        },
      };

      expect(traderWithoutConfig.latest_config).toBeUndefined();
      expect(traderWithConfig.latest_config).toBeDefined();
    });
  });

  describe('ValidationError', () => {
    it('should accept FastAPI validation error structure', () => {
      const error: ValidationError = {
        type: 'value_error',
        loc: ['body', 'wallet_address'],
        msg: 'Field required',
        input: null,
      };

      expect(error.type).toBe('value_error');
      expect(error.loc).toEqual(['body', 'wallet_address']);
      expect(error.msg).toBe('Field required');
    });

    it('should accept validation error without input field', () => {
      const error: ValidationError = {
        type: 'missing',
        loc: ['body', 'config', 'name'],
        msg: 'Field required',
      };

      expect(error.input).toBeUndefined();
    });
  });

  describe('ApiError', () => {
    it('should accept string detail', () => {
      const error: ApiError = {
        detail: 'Something went wrong',
      };

      expect(error.detail).toBe('Something went wrong');
    });

    it('should accept array of ValidationError as detail', () => {
      const error: ApiError = {
        detail: [
          {
            type: 'value_error',
            loc: ['body', 'wallet_address'],
            msg: 'Field required',
          },
          {
            type: 'value_error',
            loc: ['body', 'private_key'],
            msg: 'Invalid format',
          },
        ],
      };

      if (Array.isArray(error.detail)) {
        expect(error.detail).toHaveLength(2);
        expect(error.detail[0].msg).toBe('Field required');
        expect(error.detail[1].msg).toBe('Invalid format');
      }
    });
  });

  describe('NetworkType', () => {
    it('should only accept testnet or mainnet', () => {
      const testnet: NetworkType = 'testnet';
      const mainnet: NetworkType = 'mainnet';

      expect(testnet).toBe('testnet');
      expect(mainnet).toBe('mainnet');
    });
  });

  describe('ExchangeType', () => {
    it('should only accept hyperliquid', () => {
      const exchange: ExchangeType = 'hyperliquid';

      expect(exchange).toBe('hyperliquid');
    });
  });

  describe('User types', () => {
    it('models local auth user shape', () => {
      const user: User = {
        id: 'user-123',
        username: 'testuser',
        is_admin: false,
      };

      expect(user.username).toBe('testuser');
      expect(user.is_admin).toBe(false);
    });

    it('should accept valid LoginRequest', () => {
      const loginRequest: LoginRequest = {
        username: 'testuser',
        password: 'password123',
      };

      expect(loginRequest.username).toBe('testuser');
      expect(loginRequest.password).toBe('password123');
    });

    it('should accept valid LoginResponse', () => {
      const loginResponse: LoginResponse = {
        access_token: 'eyJhbGciOiJIUzI1NiIs...',
        token_type: 'bearer',
        user: {
          id: 'user-123',
          username: 'testuser',
          is_admin: false,
        },
      };

      expect(loginResponse.token_type).toBe('bearer');
      expect(loginResponse.user.username).toBe('testuser');
    });
  });
});
