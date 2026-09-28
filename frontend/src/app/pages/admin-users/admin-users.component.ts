import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { Role, User } from '../../core/models/models';

const ROLES: Role[] = ['admin', 'gate_controller', 'ground_staff', 'passenger'];

@Component({
  selector: 'app-admin-users',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './admin-users.component.html',
  styleUrl: './admin-users.component.css',
})
export class AdminUsersComponent implements OnInit {
  roles = ROLES;
  users = signal<User[]>([]);
  loading = signal(false);
  error = signal('');
  message = signal('');

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.load();
  }

  load() {
    this.loading.set(true);
    this.api.listUsers().subscribe({
      next: (u) => {
        this.users.set(u);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Failed to load users.');
        this.loading.set(false);
      },
    });
  }

  changeRole(user: User, role: string) {
    this.message.set('');
    this.api.updateUserRole(user.id, role).subscribe({
      next: () => {
        this.message.set(`${user.username} is now ${role}.`);
        this.load();
      },
      error: (err) => this.error.set(err?.error?.message || 'Failed to update role.'),
    });
  }

  toggleActive(user: User) {
    this.api.deactivateUser(user.id, !user.is_active).subscribe({
      next: () => this.load(),
      error: (err) => this.error.set(err?.error?.message || 'Failed to update user status.'),
    });
  }
}
