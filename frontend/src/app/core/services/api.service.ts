import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  Flight,
  Gate,
  GateAssignment,
  GateAssignmentReportRow,
  ServiceRequest,
  ServiceRequestAnalytics,
  User,
} from '../models/models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // Gates
  listGates(): Observable<Gate[]> {
    return this.http.get<Gate[]>(`${this.base}/gates`);
  }
  createGate(payload: Partial<Gate>): Observable<Gate> {
    return this.http.post<Gate>(`${this.base}/gates`, payload);
  }
  updateGate(id: number, payload: Partial<Gate>): Observable<Gate> {
    return this.http.patch<Gate>(`${this.base}/gates/${id}`, payload);
  }

  // Flights
  listFlights(statusFilter?: string): Observable<Flight[]> {
    const q = statusFilter ? `?status=${statusFilter}` : '';
    return this.http.get<Flight[]>(`${this.base}/flights${q}`);
  }
  createFlight(payload: Partial<Flight>): Observable<Flight> {
    return this.http.post<Flight>(`${this.base}/flights`, payload);
  }
  updateFlightStatus(id: number, status: string): Observable<Flight> {
    return this.http.patch<Flight>(`${this.base}/flights/${id}/status`, { status });
  }

  // Gate assignments
  listGateAssignments(): Observable<GateAssignment[]> {
    return this.http.get<GateAssignment[]>(`${this.base}/gate-assignments`);
  }
  getGateAssignmentsByDate(date: string): Observable<GateAssignment[]> {
    return this.http.get<GateAssignment[]>(`${this.base}/gate-assignments/date/${date}`);
  }
  createGateAssignment(payload: {
    gate: number; flight: number; start_time: string; end_time: string; notes?: string; override?: boolean;
  }): Observable<GateAssignment> {
    return this.http.post<GateAssignment>(`${this.base}/gate-assignments`, payload);
  }
  updateGateAssignment(id: number, payload: Partial<GateAssignment> & { override?: boolean }): Observable<GateAssignment> {
    return this.http.patch<GateAssignment>(`${this.base}/gate-assignments/${id}`, payload);
  }
  deleteGateAssignment(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/gate-assignments/${id}`);
  }

  // Service requests
  listServiceRequests(params?: { status?: string; category?: string; flight_no?: string }): Observable<ServiceRequest[]> {
    const query = params
      ? '?' + Object.entries(params).filter(([, v]) => !!v).map(([k, v]) => `${k}=${v}`).join('&')
      : '';
    return this.http.get<ServiceRequest[]>(`${this.base}/service-requests${query}`);
  }
  createServiceRequest(payload: { flight_no: string; category: string; details: string }): Observable<ServiceRequest> {
    return this.http.post<ServiceRequest>(`${this.base}/service-requests`, payload);
  }
  updateServiceRequest(id: number, payload: { status?: string; assigned_to?: number; resolution_notes?: string }): Observable<ServiceRequest> {
    return this.http.patch<ServiceRequest>(`${this.base}/service-requests/${id}`, payload);
  }

  // Reports
  gateAssignmentReport(from_date: string, to_date: string, gate_number?: string): Observable<{ count: number; results: GateAssignmentReportRow[] }> {
    let q = `?from_date=${from_date}&to_date=${to_date}`;
    if (gate_number) q += `&gate_number=${gate_number}`;
    return this.http.get<{ count: number; results: GateAssignmentReportRow[] }>(`${this.base}/reports/gate-assignments${q}`);
  }
  downloadGateAssignmentReportCsv(from_date: string, to_date: string, gate_number?: string): Observable<Blob> {
    let q = `?from_date=${from_date}&to_date=${to_date}&export=csv`;
    if (gate_number) q += `&gate_number=${gate_number}`;
    return this.http.get(`${this.base}/reports/gate-assignments${q}`, { responseType: 'blob' });
  }
  serviceRequestAnalytics(params?: { from_date?: string; to_date?: string; category?: string; status?: string }): Observable<ServiceRequestAnalytics> {
    const query = params
      ? '?' + Object.entries(params).filter(([, v]) => !!v).map(([k, v]) => `${k}=${v}`).join('&')
      : '';
    return this.http.get<ServiceRequestAnalytics>(`${this.base}/reports/service-requests${query}`);
  }

  // Staff / admin
  listGroundStaff(): Observable<{ id: number; username: string; email: string }[]> {
    return this.http.get<{ id: number; username: string; email: string }[]>(`${this.base}/staff/ground-staff`);
  }
  listUsers(): Observable<User[]> {
    return this.http.get<User[]>(`${this.base}/admin/users`);
  }
  updateUserRole(id: number, role: string): Observable<User> {
    return this.http.patch<User>(`${this.base}/admin/users/${id}/role`, { role });
  }
  deactivateUser(id: number, is_active: boolean): Observable<User> {
    return this.http.patch<User>(`${this.base}/admin/users/${id}/deactivate`, { is_active });
  }
}
