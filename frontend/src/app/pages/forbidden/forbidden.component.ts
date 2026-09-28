import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-forbidden',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div style="padding:3rem;text-align:center;">
      <h1>403 — Insufficient permissions</h1>
      <p>You do not have access to this page.</p>
      <a routerLink="/">Go home</a>
    </div>
  `,
})
export class ForbiddenComponent {}
