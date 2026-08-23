/**
 * API Client placeholder
 * This will eventually handle axios/fetch configuration and interceptors
 */

export const apiClient = {
  get: async (url: string) => {
    throw new Error(`Not implemented: GET ${url}`);
  },
  post: async (url: string, data: any) => {
    throw new Error(`Not implemented: POST ${url} with data ${JSON.stringify(data)}`);
  }
};
