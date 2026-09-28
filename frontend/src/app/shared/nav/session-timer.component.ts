import { Component, OnDestroy, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-session-timer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <span class="session-timer" [class.warn]="isExpiringSoon()" *ngIf="auth.accessTokenExpiry()">
      Session expires in {{ remaining() }}
    </span>
  `,
  styles: [`
    .session-timer { font-size: 0.8rem; color: #6b7280; }
    .session-timer.warn { color: #dc2626; font-weight: 600; }
  `],
})
export class SessionTimerComponent implements OnInit, OnDestroy {
  now = signal(Date.now());
  private intervalId?: ReturnType<typeof setInterval>;

  constructor(public auth: AuthService) {}

  ngOnInit() {
    this.intervalId = setInterval(() => this.now.set(Date.now()), 1000);
  }

  ngOnDestroy() {
    if (this.intervalId) clearInterval(this.intervalId);
  }

  remaining = computed(() => {
    const exp = this.auth.accessTokenExpiry();
    if (!exp) return '';
    const diffMs = exp - this.now();
    if (diffMs <= 0) return 'expired — please log in again';
    const totalSeconds = Math.floor(diffMs / 1000);
    const h = Math.floor(totalSeconds / 3600);
    const m = Math.floor((totalSeconds % 3600) / 60);
    const s = totalSeconds % 60;
    return h > 0 ? `${h}h ${m}m` : `${m}m ${s}s`;
  });

  isExpiringSoon = computed(() => {
    const exp = this.auth.accessTokenExpiry();
    if (!exp) return false;
    return exp - this.now() < 5 * 60 * 1000;
  });
}
