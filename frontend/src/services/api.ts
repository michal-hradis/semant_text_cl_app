import { api } from 'boot/axios';
import {
  LoginRequest,
  BearerResponse,
  UserRead,
  UserCreate,
  RatingRequest,
  RatingResponseNew,
} from 'src/types/api';

class ApiService {
  // Authentication
  async login(credentials: LoginRequest): Promise<BearerResponse> {
    const formData = new URLSearchParams();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);

    const response = await api.post<BearerResponse>(
      '/auth/jwt/login',
      formData,
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      }
    );
    return response.data;
  }

  async logout(): Promise<void> {
    await api.post('/auth/jwt/logout');
  }

  async getCurrentUser(): Promise<UserRead> {
    const response = await api.get<UserRead>('/users/me');
    return response.data;
  }

  async register(userData: UserCreate): Promise<UserRead> {
    const response = await api.post<UserRead>('/auth/register', userData);
    return response.data;
  }

  // Rating endpoints
  async getRatingRequest(): Promise<RatingRequest> {
    const response = await api.get<RatingRequest>('/api/rating/request');
    return response.data;
  }

  async submitRatingResponse(response: RatingResponseNew): Promise<void> {
    await api.post('/api/rating/response', response);
  }
}

export const apiService = new ApiService();
