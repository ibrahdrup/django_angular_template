import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const token = auth.getAccessToken();
  const isAuthCall = req.url.includes('/auth/login') || req.url.includes('/auth/register') || req.url.includes('/auth/refresh');

  const authReq = token && !isAuthCall
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(authReq).pipe(
    catchError((err: HttpErrorResponse) => {
      if (err.status === 401 && !isAuthCall && auth.getRefreshToken()) {
        return auth.refreshAccessToken().pipe(
          switchMap((res) => {
            const retried = req.clone({ setHeaders: { Authorization: `Bearer ${res.access}` } });
            return next(retried);
          }),
          catchError((refreshErr) => {
            auth.clearSession();
            return throwError(() => refreshErr);
          })
        );
      }
      return throwError(() => err);
    })
  );
};
