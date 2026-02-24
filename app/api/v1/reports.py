from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.dependencies import get_admin_user
from app.models.user import User
from app.models.booking import Booking, BookingStatus
from app.models.resource import Resource, ResourceType
from app.models.vehicle import Vehicle
from app.models.driver import Driver
from app.models.driver_assignment import DriverAssignment
from app.models.fuel_expense import FuelExpense, FuelType
from app.models.maintenance_record import MaintenanceRecord
from app.models.driver_rating import DriverRating
from app.schemas.common import success_response

router = APIRouter(prefix="/reports")


# ─── Booking Summary ──────────────────────────────────────────────────────────
@router.get("/bookings", summary="Booking summary report (Admin)")
def report_bookings(
    startDate:    Optional[str] = Query(None),
    endDate:      Optional[str] = Query(None),
    resourceType: Optional[str] = Query(None, description="VEHICLE | ROOM"),
    departmentId: Optional[int] = Query(None),
    db:           Session       = Depends(get_db),
    _:            User          = Depends(get_admin_user),
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

    by_type = {}
    for b in bookings:
        t = b.resource.type.value
        by_type[t] = by_type.get(t, 0) + 1

    dept_map = {}
    for b in bookings:
        dept = b.user.department.name
        dept_map[dept] = dept_map.get(dept, 0) + 1
    by_department = [{"department": k, "total": v} for k, v in sorted(dept_map.items(), key=lambda x: -x[1])]

    return success_response("Booking report generated", {
        "period":  {"startDate": startDate, "endDate": endDate},
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
    resourceType: Optional[str] = Query(None),
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
            "resourceId":        r.id,
            "resourceName":      r.name,
            "resourceType":      r.type.value,
            "status":            r.status.value,
            "totalBookings":     len(all_bookings),
            "completedBookings": len(completed),
            "utilizationRate":   round(len(completed) / len(all_bookings) * 100, 1) if all_bookings else 0,
        })

    result.sort(key=lambda x: -x["totalBookings"])
    return success_response("Resource utilization report generated", {
        "period":    {"startDate": startDate, "endDate": endDate},
        "resources": result,
    })


# ─── Fuel Expense Report (BBM + Listrik) ─────────────────────────────────────
@router.get("/fuel-expenses", summary="Comprehensive fuel expense report — BBM & Listrik (Admin)")
def report_fuel_expenses(
    startDate: Optional[str] = Query(None),
    endDate:   Optional[str] = Query(None),
    vehicleId: Optional[int] = Query(None),
    driverId:  Optional[int] = Query(None),
    fuelType:  Optional[str] = Query(None, description="BBM | LISTRIK"),
    db:        Session       = Depends(get_db),
    _:         User          = Depends(get_admin_user),
):
    q = db.query(FuelExpense)
    if startDate: q = q.filter(FuelExpense.createdAt >= startDate)
    if endDate:   q = q.filter(FuelExpense.createdAt <= endDate)
    if vehicleId: q = q.filter(FuelExpense.vehicleId == vehicleId)
    if driverId:  q = q.filter(FuelExpense.driverId  == driverId)
    if fuelType:  q = q.filter(FuelExpense.fuelType  == fuelType)

    expenses = q.all()
    bbm_expenses     = [e for e in expenses if e.fuelType == FuelType.BBM]
    listrik_expenses = [e for e in expenses if e.fuelType == FuelType.LISTRIK]

    total_amount = sum(float(e.totalAmount) for e in expenses)

    # Per vehicle
    vehicle_map = {}
    for e in expenses:
        key = e.vehicle.plateNumber
        if key not in vehicle_map:
            vehicle_map[key] = {
                "plateNumber": key,
                "brand":  e.vehicle.brand,
                "model":  e.vehicle.model,
                "bbmLiter": 0, "bbmAmount": 0,
                "kwhUsed":  0, "listrikAmount": 0,
                "totalAmount": 0, "entries": 0,
            }
        vehicle_map[key]["totalAmount"] += float(e.totalAmount)
        vehicle_map[key]["entries"]     += 1
        if e.fuelType == FuelType.BBM:
            vehicle_map[key]["bbmLiter"]  += float(e.liter or 0)
            vehicle_map[key]["bbmAmount"] += float(e.totalAmount)
        else:
            vehicle_map[key]["kwhUsed"]       += float(e.kwh or 0)
            vehicle_map[key]["listrikAmount"]  += float(e.totalAmount)

    # Per driver
    driver_map = {}
    for e in expenses:
        key = e.driver.user.name
        if key not in driver_map:
            driver_map[key] = {"driverName": key, "bbmAmount": 0, "listrikAmount": 0, "totalAmount": 0, "entries": 0}
        driver_map[key]["totalAmount"] += float(e.totalAmount)
        driver_map[key]["entries"]     += 1
        if e.fuelType == FuelType.BBM:
            driver_map[key]["bbmAmount"]     += float(e.totalAmount)
        else:
            driver_map[key]["listrikAmount"] += float(e.totalAmount)

    return success_response("Fuel expense report generated", {
        "period": {"startDate": startDate, "endDate": endDate},
        "summary": {
            "totalEntries":    len(expenses),
            "totalAmount":     round(total_amount, 2),
            "bbm": {
                "entries":     len(bbm_expenses),
                "totalLiter":  round(sum(float(e.liter or 0) for e in bbm_expenses), 2),
                "totalAmount": round(sum(float(e.totalAmount) for e in bbm_expenses), 2),
            },
            "listrik": {
                "entries":     len(listrik_expenses),
                "totalKwh":    round(sum(float(e.kwh or 0) for e in listrik_expenses), 2),
                "totalAmount": round(sum(float(e.totalAmount) for e in listrik_expenses), 2),
            },
        },
        "byVehicle": sorted(vehicle_map.values(), key=lambda x: -x["totalAmount"]),
        "byDriver":  sorted(driver_map.values(),  key=lambda x: -x["totalAmount"]),
    })


# ─── Maintenance Cost Report ──────────────────────────────────────────────────
@router.get("/maintenance-cost", summary="Maintenance cost report — vehicles & rooms (Admin)")
def report_maintenance_cost(
    startDate:    Optional[str] = Query(None),
    endDate:      Optional[str] = Query(None),
    resourceType: Optional[str] = Query(None, description="VEHICLE | ROOM"),
    db:           Session       = Depends(get_db),
    _:            User          = Depends(get_admin_user),
):
    q = db.query(MaintenanceRecord).join(MaintenanceRecord.resource)
    if startDate:    q = q.filter(MaintenanceRecord.startDate >= startDate)
    if endDate:      q = q.filter(MaintenanceRecord.startDate <= endDate)
    if resourceType: q = q.filter(Resource.type == resourceType)

    records   = q.all()
    total_cost = sum(float(r.cost) for r in records if r.cost)
    ongoing    = [r for r in records if r.endDate is None]

    # By resource type
    by_type_map: dict = {}
    for r in records:
        t = r.resource.type.value
        if t not in by_type_map:
            by_type_map[t] = {"type": t, "totalCost": 0, "count": 0}
        by_type_map[t]["totalCost"] += float(r.cost or 0)
        by_type_map[t]["count"]     += 1

    return success_response("Maintenance cost report generated", {
        "period": {"startDate": startDate, "endDate": endDate},
        "summary": {
            "totalRecords":   len(records),
            "ongoingCount":   len(ongoing),
            "completedCount": len(records) - len(ongoing),
            "totalCost":      round(total_cost, 2),
        },
        "byResourceType": list(by_type_map.values()),
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


# ─── Driver Rating Report ─────────────────────────────────────────────────────
@router.get("/driver-ratings", summary="Driver rating & evaluation report (Admin)")
def report_driver_ratings(
    driverId: Optional[int] = Query(None),
    db:       Session       = Depends(get_db),
    _:        User          = Depends(get_admin_user),
):
    q = db.query(Driver)
    if driverId: q = q.filter(Driver.id == driverId)
    drivers = q.all()

    result = []
    for d in drivers:
        ratings = db.query(DriverRating).filter(DriverRating.driverId == d.id).all()
        avg = round(sum(r.rating for r in ratings) / len(ratings), 2) if ratings else None
        result.append({
            "driverId":      d.id,
            "driverName":    d.user.name,
            "isActive":      d.isActive,
            "totalRatings":  len(ratings),
            "averageRating": avg,
            "ratingBreakdown": {
                str(i): sum(1 for r in ratings if r.rating == i) for i in range(1, 6)
            },
            "recentReviews": [{
                "rating":    r.rating,
                "review":    r.review,
                "ratedBy":   r.rated_by.name,
                "createdAt": r.createdAt.isoformat(),
            } for r in sorted(ratings, key=lambda x: x.createdAt, reverse=True)[:5]],
        })

    result.sort(key=lambda x: (x["averageRating"] or 0), reverse=True)
    return success_response("Driver rating report generated", {"drivers": result})


# ─── Driver Activity ──────────────────────────────────────────────────────────
@router.get("/driver-activity", summary="Driver usage & fuel summary (Admin)")
def report_driver_activity(
    startDate: Optional[str] = Query(None),
    endDate:   Optional[str] = Query(None),
    db:        Session       = Depends(get_db),
    _:         User          = Depends(get_admin_user),
):
    drivers = db.query(Driver).all()
    result  = []

    for d in drivers:
        active = next((a for a in d.assignments if a.releasedAt is None), None)
        fe_q   = db.query(FuelExpense).filter(FuelExpense.driverId == d.id)
        if startDate: fe_q = fe_q.filter(FuelExpense.createdAt >= startDate)
        if endDate:   fe_q = fe_q.filter(FuelExpense.createdAt <= endDate)
        fes = fe_q.all()

        bbm_fes     = [e for e in fes if e.fuelType == FuelType.BBM]
        listrik_fes = [e for e in fes if e.fuelType == FuelType.LISTRIK]

        ratings = db.query(DriverRating).filter(DriverRating.driverId == d.id).all()
        avg_rating = round(sum(r.rating for r in ratings) / len(ratings), 2) if ratings else None

        result.append({
            "driverId":   d.id,
            "driverName": d.user.name,
            "employeeId": d.user.employeeId,
            "isActive":   d.isActive,
            "currentVehicle": {
                "id":          active.vehicle.id,
                "plateNumber": active.vehicle.plateNumber,
            } if active else None,
            "totalAssignments": len(d.assignments),
            "averageRating":    avg_rating,
            "totalRatings":     len(ratings),
            "fuelSummary": {
                "totalEntries":  len(fes),
                "totalAmount":   round(sum(float(e.totalAmount) for e in fes), 2),
                "bbm": {
                    "entries":     len(bbm_fes),
                    "totalLiter":  round(sum(float(e.liter or 0) for e in bbm_fes), 2),
                    "totalAmount": round(sum(float(e.totalAmount) for e in bbm_fes), 2),
                },
                "listrik": {
                    "entries":     len(listrik_fes),
                    "totalKwh":    round(sum(float(e.kwh or 0) for e in listrik_fes), 2),
                    "totalAmount": round(sum(float(e.totalAmount) for e in listrik_fes), 2),
                },
            },
        })

    return success_response("Driver activity report generated", {
        "period":  {"startDate": startDate, "endDate": endDate},
        "drivers": sorted(result, key=lambda x: -x["fuelSummary"]["totalAmount"]),
    })


# ─── Overdue Bookings ─────────────────────────────────────────────────────────
@router.get("/overdue-bookings", summary="Current overdue bookings (Admin)")
def report_overdue(
    db: Session = Depends(get_db),
    _:  User    = Depends(get_admin_user),
):
    bookings = db.query(Booking).filter(Booking.status == BookingStatus.OVERDUE).all()
    return success_response("Overdue bookings retrieved", {
        "total": len(bookings),
        "bookings": [{
            "id":       b.id,
            "user":     {"id": b.user.id, "name": b.user.name, "employeeId": b.user.employeeId},
            "resource": {"id": b.resource.id, "name": b.resource.name, "type": b.resource.type.value},
            "startDate": b.startDate.isoformat(),
            "endDate":   b.endDate.isoformat(),
            "purpose":   b.purpose,
            "approvedBy": b.approved_by.name if b.approved_by else None,
        } for b in bookings],
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
