import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './register.component.html',
  styleUrl: '../login/auth-pages.css',
})
export class RegisterComponent {
  username = '';
  email = '';
  password = '';
  confirmPassword = '';
  loading = signal(false);
  error = signal('');
  success = signal(false);

  constructor(private auth: AuthService, private router: Router) {}

  submit() {
    this.error.set('');
    if (!this.username || !this.email || !this.password) {
      this.error.set('All fields are required.');
      return;
    }
    if (this.password.length < 8) {
      this.error.set('Password must be at least 8 characters.');
      return;
    }
    if (this.password !== this.confirmPassword) {
      this.error.set('Passwords do not match.');
      return;
    }
    this.loading.set(true);
    this.auth.register(this.username, this.email, this.password).subscribe({
      next: () => {
        this.loading.set(false);
        this.success.set(true);
        setTimeout(() => this.router.navigate(['/login']), 1200);
      },
      error: (err) => {
        this.loading.set(false);
        const msg = err?.error?.message || err?.error?.errors ? JSON.stringify(err.error.errors) : 'Registration failed.';
        this.error.set(err?.error?.message || msg);
      },
    });
  }
}
