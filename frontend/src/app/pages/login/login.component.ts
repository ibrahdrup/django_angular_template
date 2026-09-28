import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './login.component.html',
  styleUrl: './auth-pages.css',
})
export class LoginComponent {
  username = '';
  password = '';
  loading = signal(false);
  error = signal('');

  constructor(private auth: AuthService, private router: Router) {}

  submit() {
    this.error.set('');
    if (!this.username || !this.password) {
      this.error.set('Username and password are required.');
      return;
    }
    this.loading.set(true);
    this.auth.login(this.username, this.password).subscribe({
      next: (res) => {
        this.loading.set(false);
        if (res.user.role === 'passenger') {
          this.router.navigate(['/service-requests']);
        } else {
          this.router.navigate(['/dashboard']);
        }
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set(err?.error?.message || 'Invalid username or password.');
      },
    });
  }
}
