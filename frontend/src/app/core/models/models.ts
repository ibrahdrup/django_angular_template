export type Role = 'admin' | 'gate_controller' | 'ground_staff' | 'passenger';

export interface User {
  id: number;
  username: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface AuthResponse {
  access: string;
  refresh: string;
  user: { id: number; username: string; email: string; role: Role };
}

export type GateType = 'domestic' | 'international' | 'cargo';
export type GateStatus = 'operational' | 'under_maintenance' | 'closed';

export interface Gate {
  id: number;
  gate_number: string;
  terminal: string;
  gate_type: GateType;
  status: GateStatus;
}

export type FlightStatus = 'scheduled' | 'assigned' | 'delayed' | 'boarding' | 'departed' | 'cancelled' | 'arrived';

export interface Flight {
  id: number;
  flight_no: string;
  airline: string;
  origin: string;
  destination: string;
  aircraft_type: string;
  flight_type: GateType;
  scheduled_arrival: string;
  scheduled_departure: string;
  status: FlightStatus;
}

export type AssignmentStatus = 'scheduled' | 'assigned' | 'delayed' | 'boarding' | 'departed' | 'cancelled';

export interface GateAssignment {
  id: number;
  gate: number;
  gate_number: string;
  flight: number;
  flight_no: string;
  start_time: string;
  end_time: string;
  status: AssignmentStatus;
  assigned_by: number;
  assigned_by_username: string;
  notes: string | null;
  is_deleted: boolean;
}

export type ServiceRequestCategory =
  | 'food' | 'beverage' | 'wheelchair' | 'special_assistance' | 'medical' | 'lost_baggage' | 'other';
export type ServiceRequestStatus = 'open' | 'in_progress' | 'resolved' | 'rejected';

export interface ServiceRequest {
  id: number;
  passenger: number;
  passenger_username: string;
  flight: number;
  flight_no: string;
  category: ServiceRequestCategory;
  details: string;
  status: ServiceRequestStatus;
  assigned_to: number | null;
  assigned_to_username: string | null;
  resolution_notes: string | null;
  created_at: string;
  resolved_at: string | null;
}

export interface GateAssignmentReportRow {
  date: string;
  gate_number: string;
  flight_no: string;
  airline: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  status: string;
}

export interface ServiceRequestAnalytics {
  total_requests: number;
  total_resolved: number;
  total_open: number;
  open_vs_resolved_ratio: number | null;
  average_resolution_minutes: number | null;
  category_breakdown: { category: string; count: number }[];
  status_breakdown: { status: string; count: number }[];
  staff_breakdown: { assigned_to__id: number; assigned_to__username: string; count: number }[];
}
