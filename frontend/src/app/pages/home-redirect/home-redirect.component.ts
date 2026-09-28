import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-home-redirect',
  standalone: true,
  template: '',
})
export class HomeRedirectComponent implements OnInit {
  constructor(private auth: AuthService, private router: Router) {}

  ngOnInit() {
    if (this.auth.hasRole('passenger')) {
      this.router.navigate(['/service-requests']);
    } else {
      this.router.navigate(['/dashboard']);
    }
  }
}
