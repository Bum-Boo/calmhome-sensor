# Sensor Placement Guide

Placement determines whether the beta feels reliable. Test with consented residents before using alerts.

## Desk Or Rear-Presence Reassurance Mode

Goal: show that someone remains present at a desk, chair, or work area.

Recommendations:

- Place the sensor where it can see the seated area without pointing into a hallway.
- Mount it at chest height or slightly above when seated.
- Angle it away from fans, moving curtains, and windows.
- Use still-presence as the most important signal.
- Keep fall status disabled unless the room layout supports meaningful testing.

## Bedroom Elder-Care Mode

Goal: show room presence, long inactivity, and fall suspected status with minimal disturbance.

Recommendations:

- Place the presence sensor where it covers the bed exit path and common standing area.
- Place fall status hardware according to the vendor mounting guidance.
- Test lying down, sitting at the bed edge, walking, and leaving the room.
- Use conservative alert timing. Long inactivity should not notify too quickly.
- Discuss notification recipients and quiet hours with all residents.

## Living Room Presence Mode

Goal: detect occupancy and movement in a shared room.

Recommendations:

- Mount the sensor with a broad view of seating and walking paths.
- Avoid direct aim at TVs, fans, curtains, and reflective surfaces.
- Expect more multi-person ambiguity. The beta summarizes room state, not person count.
- Use dashboard summaries first, then enable notifications only after several days of testing.

## Entrance And Door-Combination Mode

Goal: combine occupancy with a door contact sensor.

Recommendations:

- Place the door contact on the room door.
- Keep presence coverage inside the room, not beyond the doorway.
- Use the door-opened-while-occupied automation for local status logging.
- Avoid using door activity alone as a safety alert.

## Common False Positives

- Fan movement: oscillating fans can look like motion.
- Curtains: airflow can create repeated movement.
- Pets: small animals may trigger presence or movement depending on sensitivity and mounting height.
- Reflective surfaces: mirrors, glass, and metal can cause confusing returns.
- Sensor angle: small angle changes can create large behavior changes.
- Multiple people: this beta only summarizes room state and does not track individuals.

## Calibration Checklist

- Confirm all residents consent to the room and sensor placement.
- Start with mock mode and confirm dashboard behavior.
- Confirm each ESPHome entity appears in Home Assistant.
- Map CalmHome helpers to real entity IDs.
- Test room empty for at least 10 minutes.
- Test normal entry and exit.
- Test seated still presence for at least 10 minutes.
- Test walking movement for at least 30 seconds.
- Test door opened while occupied.
- Test sensor offline by powering down the ESPHome device briefly.
- Enable notifications only after the dashboard states are stable.
- Recheck after moving furniture, adding fans, or changing curtains.
