from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import Optional

from app.database import get_db
from app.dependencies import get_approver_or_admin, get_admin_user
from app.models.user import User
from app.models.booking import Booking, BookingStatus
from app.models.resource import Resource, ResourceType
from app.models.vehicle import Vehicle
from app.models.driver import Driver
from app.models.driver_assignment import DriverAssignment
from app.models.fuel_expense import FuelExpense
from app.models.maintenance_record import MaintenanceRecord
from app.models.department import Department
from app.schemas.common import success_response

router = APIRouter(prefix="/reports")


# ─── Booking Summary ──────────────────────────────────────────────────────────
@router.get("/bookings", summary="Booking summary report (Approver/Admin)")
def report_bookings(
    startDate:    Optional[str] = Query(None, description="ISO 8601 e.g. 2024-03-01"),
    endDate:      Optional[str] = Query(None),
    resourceType: Optional[str] = Query(None, description="VEHICLE | ROOM"),
    departmentId: Optional[int] = Query(None),
    db:           Session       = Depends(get_db),
    _:            User          = Depends(get_approver_or_admin),
):
    q = db.query(Booking)
    if startDate:    q = q.filter(Booking.createdAt >= startDate)
    if endDate:      q = q.filter(Booking.createdAt <= endDate)
    if resourceType:
        q = q.join(Resource, Booking.resourceId == Resource.id)\
             .filter(Resource.type == resourceType)
    if departmentId:
        q = q.join(User, Booking.userId == User.id)\
             .filter(User.departmentId == departmentId)

    bookings = q.all()
    total    = len(bookings)

    def count_status(s): return sum(1 for b in bookings if b.status == s)

    # By resource type
    by_type = {}
    for b in bookings:
        t = b.resource.type.value
        by_type[t] = by_type.get(t, 0) + 1

    # By department
    dept_map = {}
    for b in bookings:
        dept = b.user.department.name
        dept_map[dept] = dept_map.get(dept, 0) + 1
    by_department = [{"department": k, "total": v} for k, v in sorted(dept_map.items(), key=lambda x: -x[1])]

    return success_response("Booking report generated", {
        "period": {"startDate": startDate, "endDate": endDate},
        "summary": {
            "total":     total,
            "pending":   count_status(BookingStatus.PENDING),
            "approved":  count_status(BookingStatus.APPROVED),
            "rejected":  count_status(BookingStatus.REJECTED),
            "ongoing":   count_status(BookingStatus.ONGOING),
            "completed": count_status(BookingStatus.COMPLETED),
            "cancelled": count_status(BookingStatus.CANCELLED),
            "overdue":   count_status(BookingStatus.OVERDUE),
        },
        "byResourceType": by_type,
        "byDepartment":   by_department,
    })


# ─── Resource Utilization ─────────────────────────────────────────────────────
@router.get("/resource-usage", summary="Resource utilization report (Admin)")
def report_resource_usage(
    startDate:    Optional[str] = Query(None),
    endDate:      Optional[str] = Query(None),
    resourceType: Optional[str] = Query(None, description="VEHICLE | ROOM"),
    db:           Session       = Depends(get_db),
    _:            User          = Depends(get_admin_user),
):
    q = db.query(Resource)
    if resourceType: q = q.filter(Resource.type == resourceType)
    resources = q.all()

    result = []
    for r in resources:
        bq = db.query(Booking).filter(Booking.resourceId == r.id)
        if startDate: bq = bq.filter(Booking.startDate >= startDate)
        if endDate:   bq = bq.filter(Booking.endDate   <= endDate)

        all_bookings = bq.all()
        completed    = [b for b in all_bookings if b.status == BookingStatus.COMPLETED]

        result.append({
            "resourceId":   r.id,
            "resourceName": r.name,
            "resourceType": r.type.value,
            "status":       r.status.value,
            "totalBookings":    len(all_bookings),
            "completedBookings":len(completed),
            "utilizationRate":  round(len(completed) / len(all_bookings) * 100, 1) if all_bookings else 0,
        })

    result.sort(key=lambda x: -x["totalBookings"])
    return success_response("Resource utilization report generated", {
        "period": {"startDate": startDate, "endDate": endDate},
        "resources": result,
    })


# ─── Fuel Expense Report ──────────────────────────────────────────────────────
@router.get("/fuel-expenses", summary="Fuel expense report (Admin)")
def report_fuel_expenses(
    startDate: Optional[str] = Query(None),
    endDate:   Optional[str] = Query(None),
    vehicleId: Optional[int] = Query(None),
    driverId:  Optional[int] = Query(None),
    db:        Session       = Depends(get_db),
    _:         User          = Depends(get_admin_user),
):
    q = db.query(FuelExpense)
    if startDate: q = q.filter(FuelExpense.createdAt >= startDate)
    if endDate:   q = q.filter(FuelExpense.createdAt <= endDate)
    if vehicleId: q = q.filter(FuelExpense.vehicleId == vehicleId)
    if driverId:  q = q.filter(FuelExpense.driverId  == driverId)

    expenses = q.all()

    total_liter  = sum(float(e.liter) for e in expenses)
    total_amount = sum(float(e.totalAmount) for e in expenses)

    # Per vehicle
    vehicle_map = {}
    for e in expenses:
        key = e.vehicle.plateNumber
        if key not in vehicle_map:
            vehicle_map[key] = {"plateNumber": key, "brand": e.vehicle.brand,
                                "model": e.vehicle.model, "totalLiter": 0, "totalAmount": 0, "entries": 0}
        vehicle_map[key]["totalLiter"]  += float(e.liter)
        vehicle_map[key]["totalAmount"] += float(e.totalAmount)
        vehicle_map[key]["entries"]     += 1

    # Per driver
    driver_map = {}
    for e in expenses:
        key = e.driver.user.name
        if key not in driver_map:
            driver_map[key] = {"driverName": key, "totalLiter": 0, "totalAmount": 0, "entries": 0}
        driver_map[key]["totalLiter"]  += float(e.liter)
        driver_map[key]["totalAmount"] += float(e.totalAmount)
        driver_map[key]["entries"]     += 1

    return success_response("Fuel expense report generated", {
        "period": {"startDate": startDate, "endDate": endDate},
        "summary": {
            "totalEntries": len(expenses),
            "totalLiter":   round(total_liter, 2),
            "totalAmount":  round(total_amount, 2),
            "avgPerEntry":  round(total_amount / len(expenses), 2) if expenses else 0,
        },
        "byVehicle": sorted(vehicle_map.values(), key=lambda x: -x["totalAmount"]),
        "byDriver":  sorted(driver_map.values(),  key=lambda x: -x["totalAmount"]),
    })


# ─── Maintenance Cost Report ──────────────────────────────────────────────────
@router.get("/maintenance-cost", summary="Maintenance cost report (Admin)")
def report_maintenance_cost(
    startDate:    Optional[str] = Query(None),
    endDate:      Optional[str] = Query(None),
    resourceType: Optional[str] = Query(None),
    db:           Session       = Depends(get_db),
    _:            User          = Depends(get_admin_user),
):
    q = db.query(MaintenanceRecord).join(MaintenanceRecord.resource)
    if startDate:    q = q.filter(MaintenanceRecord.startDate >= startDate)
    if endDate:      q = q.filter(MaintenanceRecord.startDate <= endDate)
    if resourceType: q = q.filter(Resource.type == resourceType)

    records = q.all()
    total_cost = sum(float(r.cost) for r in records if r.cost)
    ongoing    = [r for r in records if r.endDate is None]

    return success_response("Maintenance cost report generated", {
        "period": {"startDate": startDate, "endDate": endDate},
        "summary": {
            "totalRecords":   len(records),
            "ongoingCount":   len(ongoing),
            "completedCount": len(records) - len(ongoing),
            "totalCost":      round(total_cost, 2),
        },
        "records": [{
            "id":           r.id,
            "resourceName": r.resource.name,
            "resourceType": r.resource.type.value,
            "description":  r.description,
            "startDate":    r.startDate.isoformat(),
            "endDate":      r.endDate.isoformat() if r.endDate else None,
            "isOngoing":    r.endDate is None,
            "cost":         float(r.cost) if r.cost else None,
        } for r in records],
    })


# ─── Overdue Bookings ─────────────────────────────────────────────────────────
@router.get("/overdue-bookings", summary="Current overdue bookings (Approver/Admin)")
def report_overdue(
    db: Session = Depends(get_db),
    _:  User    = Depends(get_approver_or_admin),
):
    bookings = db.query(Booking).filter(Booking.status == BookingStatus.OVERDUE).all()
    return success_response("Overdue bookings retrieved", {
        "total": len(bookings),
        "bookings": [{
            "id":           b.id,
            "user":         {"id": b.user.id, "name": b.user.name, "employeeId": b.user.employeeId},
            "resource":     {"id": b.resource.id, "name": b.resource.name, "type": b.resource.type.value},
            "startDate":    b.startDate.isoformat(),
            "endDate":      b.endDate.isoformat(),
            "purpose":      b.purpose,
            "approvedBy":   b.approved_by.name if b.approved_by else None,
        } for b in bookings],
    })


# ─── Driver Activity ──────────────────────────────────────────────────────────
@router.get("/driver-activity", summary="Driver usage & fuel summary (Admin)")
def report_driver_activity(
    startDate: Optional[str] = Query(None),
    endDate:   Optional[str] = Query(None),
    db:        Session       = Depends(get_db),
    _:         User          = Depends(get_admin_user),
):
    drivers = db.query(Driver).all()

    result = []
    for d in drivers:
        # Assignment history count
        assign_q = db.query(DriverAssignment).filter(DriverAssignment.driverId == d.id)

        # Active assignment
        active = next((a for a in d.assignments if a.releasedAt is None), None)

        # Fuel expenses
        fe_q = db.query(FuelExpense).filter(FuelExpense.driverId == d.id)
        if startDate: fe_q = fe_q.filter(FuelExpense.createdAt >= startDate)
        if endDate:   fe_q = fe_q.filter(FuelExpense.createdAt <= endDate)
        fes = fe_q.all()

        result.append({
            "driverId":     d.id,
            "driverName":   d.user.name,
            "employeeId":   d.user.employeeId,
            "isActive":     d.isActive,
            "currentVehicle": {
                "id":          active.vehicle.id,
                "plateNumber": active.vehicle.plateNumber,
            } if active else None,
            "totalAssignments": assign_q.count(),
            "fuelSummary": {
                "entries":     len(fes),
                "totalLiter":  round(sum(float(e.liter) for e in fes), 2),
                "totalAmount": round(sum(float(e.totalAmount) for e in fes), 2),
            },
        })

    return success_response("Driver activity report generated", {
        "period": {"startDate": startDate, "endDate": endDate},
        "drivers": sorted(result, key=lambda x: -x["fuelSummary"]["totalAmount"]),
    })


# ─── Audit Logs ───────────────────────────────────────────────────────────────
@router.get("/audit-logs", summary="Audit logs (Admin)")
def get_audit_logs(
    page:       int            = Query(1, ge=1),
    limit:      int            = Query(50, ge=1, le=200),
    userId:     Optional[int]  = Query(None),
    entityType: Optional[str]  = Query(None),
    action:     Optional[str]  = Query(None),
    startDate:  Optional[str]  = Query(None),
    endDate:    Optional[str]  = Query(None),
    db:         Session        = Depends(get_db),
    _:          User           = Depends(get_admin_user),
):
    from app.models.audit_log import AuditLog
    from app.schemas.common import paginated_response

    q = db.query(AuditLog)
    if userId:     q = q.filter(AuditLog.userId     == userId)
    if entityType: q = q.filter(AuditLog.entityType == entityType)
    if action:     q = q.filter(AuditLog.action     == action)
    if startDate:  q = q.filter(AuditLog.createdAt  >= startDate)
    if endDate:    q = q.filter(AuditLog.createdAt  <= endDate)

    total = q.count()
    items = q.order_by(AuditLog.createdAt.desc()).offset((page - 1) * limit).limit(limit).all()

    data = [{
        "id":          l.id,
        "user":        {"id": l.user.id, "name": l.user.name} if l.user else None,
        "action":      l.action,
        "entityType":  l.entityType,
        "entityId":    l.entityId,
        "description": l.description,
        "createdAt":   l.createdAt.isoformat(),
    } for l in items]

    return paginated_response("Audit logs retrieved", data, total, page, limit)
