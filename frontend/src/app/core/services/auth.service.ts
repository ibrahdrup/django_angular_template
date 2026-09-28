import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthResponse, Role, User } from '../models/models';

interface JwtPayload {
  user_id: number;
  username: string;
  role: Role;
  exp: number;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly ACCESS_KEY = 'airport_ops_access';
  private readonly REFRESH_KEY = 'airport_ops_refresh';
  private readonly USER_KEY = 'airport_ops_user';

  currentUser = signal<User | null>(this.readStoredUser());
  accessTokenExpiry = signal<number | null>(this.readExpiry());

  constructor(private http: HttpClient, private router: Router) {}

  private readStoredUser(): User | null {
    const raw = localStorage.getItem(this.USER_KEY);
    return raw ? JSON.parse(raw) : null;
  }

  private readExpiry(): number | null {
    const token = localStorage.getItem(this.ACCESS_KEY);
    if (!token) return null;
    return this.decodeExpiry(token);
  }

  private decodeExpiry(token: string): number | null {
    try {
      const payload = JSON.parse(atob(token.split('.')[1])) as JwtPayload;
      return payload.exp * 1000;
    } catch {
      return null;
    }
  }

  register(username: string, email: string, password: string): Observable<User> {
    return this.http.post<User>(`${environment.apiUrl}/auth/register`, { username, email, password });
  }

  login(username: string, password: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${environment.apiUrl}/auth/login`, { username, password }).pipe(
      tap((res) => this.storeSession(res))
    );
  }

  private storeSession(res: AuthResponse) {
    localStorage.setItem(this.ACCESS_KEY, res.access);
    localStorage.setItem(this.REFRESH_KEY, res.refresh);
    localStorage.setItem(this.USER_KEY, JSON.stringify(res.user));
    this.currentUser.set(res.user as User);
    this.accessTokenExpiry.set(this.decodeExpiry(res.access));
  }

  getAccessToken(): string | null {
    return localStorage.getItem(this.ACCESS_KEY);
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(this.REFRESH_KEY);
  }

  refreshAccessToken(): Observable<{ access: string }> {
    return this.http.post<{ access: string }>(`${environment.apiUrl}/auth/refresh`, {
      refresh: this.getRefreshToken(),
    }).pipe(
      tap((res) => {
        localStorage.setItem(this.ACCESS_KEY, res.access);
        this.accessTokenExpiry.set(this.decodeExpiry(res.access));
      })
    );
  }

  logout() {
    const refresh = this.getRefreshToken();
    this.http.post(`${environment.apiUrl}/auth/logout`, { refresh }).subscribe({
      complete: () => this.clearSession(),
      error: () => this.clearSession(),
    });
  }

  clearSession() {
    localStorage.removeItem(this.ACCESS_KEY);
    localStorage.removeItem(this.REFRESH_KEY);
    localStorage.removeItem(this.USER_KEY);
    this.currentUser.set(null);
    this.accessTokenExpiry.set(null);
    this.router.navigate(['/login']);
  }

  isAuthenticated(): boolean {
    return !!this.getAccessToken();
  }

  hasRole(...roles: Role[]): boolean {
    const user = this.currentUser();
    return !!user && roles.includes(user.role);
  }
}
