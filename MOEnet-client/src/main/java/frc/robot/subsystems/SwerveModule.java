package frc.robot.subsystems;

import com.ctre.phoenix6.StatusSignal;
import com.ctre.phoenix6.hardware.CANcoder;
import com.revrobotics.CANSparkMax;
import com.revrobotics.RelativeEncoder;
import com.revrobotics.SparkPIDController;
import com.revrobotics.CANSparkLowLevel.MotorType;

import edu.wpi.first.math.MathUtil;
import edu.wpi.first.math.controller.PIDController;
import edu.wpi.first.math.geometry.Rotation2d;
import edu.wpi.first.math.geometry.Translation2d;
import edu.wpi.first.math.kinematics.SwerveModulePosition;
import edu.wpi.first.math.kinematics.SwerveModuleState;
import static edu.wpi.first.units.Units.Inches;
import static edu.wpi.first.units.Units.InchesPerSecond;
import static edu.wpi.first.units.Units.Meters;
import static edu.wpi.first.units.Units.MetersPerSecond;
import static edu.wpi.first.units.Units.RPM;
import edu.wpi.first.units.Angle;
import edu.wpi.first.units.Distance;
import edu.wpi.first.units.Measure;
import edu.wpi.first.units.Velocity;
import edu.wpi.first.util.datalog.DoubleLogEntry;
import edu.wpi.first.wpilibj.DataLogManager;
import edu.wpi.first.wpilibj.smartdashboard.SmartDashboard;

import java.util.Objects;

public class SwerveModule {
    private final Translation2d location;

    // Pivot motor
    private final String name;
    private final CANSparkMax pivotMotor;
    private final PIDController pivotPID = new PIDController(8e-3, 0, 0);
    private final CANcoder pivotAbsoluteEncoder;
    private final Rotation2d pivotAbsoluteOffset;

    // Drive motor
    private final CANSparkMax driveMotor;
    private final SparkPIDController drivePID;
    private final RelativeEncoder driveRelativeEncoder;

    // Logging
    private final DoubleLogEntry logDesiredAngle;


    public SwerveModule(String name, Translation2d location, CANSparkMax pivotMotor, CANcoder pivotAbsoluteEncoder, Rotation2d pivotAbsoluteOffset, CANSparkMax driveMotor) {
        this.name = Objects.requireNonNull(name, "Swerve module name");
        this.location = Objects.requireNonNull(location, "Swerve module location");

        // Configure pivot motor
        this.pivotMotor = Objects.requireNonNull(pivotMotor, "Swerve pivot motor");
        pivotMotor.setInverted(true);
        pivotMotor.setIdleMode(CANSparkMax.IdleMode.kBrake);

        this.pivotAbsoluteEncoder = pivotAbsoluteEncoder;
        this.pivotAbsoluteOffset = Objects.requireNonNull(pivotAbsoluteOffset, "pivotAbsoluteOffset");

        // Configure PID input to handle angle wrapping
        this.pivotPID.enableContinuousInput(-180, 180);
        // Tell SmartDashboard that our pivot is aligned if we have <4° of error
        this.pivotPID.setTolerance(4);

        // Configure drive motor
        this.driveMotor = driveMotor;
        driveMotor.setInverted(false);
        driveMotor.setIdleMode(CANSparkMax.IdleMode.kBrake);

        this.driveRelativeEncoder = driveMotor.getEncoder();

        // Configure PID
        this.drivePID = driveMotor.getPIDController();
        drivePID.setP(7.0e-5);
        drivePID.setI(0);
        drivePID.setIZone(0);
        drivePID.setD(1.0e-4);
        drivePID.setFF(1.76182e-4);
        drivePID.setOutputRange(-1,1);

        
        // Configure logs
        var log = DataLogManager.getLog();
        this.logDesiredAngle = new DoubleLogEntry(log, String.format("swerve/%s/desiredAngle", name));
    }

    public SwerveModule(String name, Translation2d location, int pivotMotorId, int pivotAbsoluteEncoderId, Rotation2d pivotAbsoluteOffset, int driveMotorId) {
        this(name, location, new CANSparkMax(pivotMotorId, MotorType.kBrushless), new CANcoder(pivotAbsoluteEncoderId), pivotAbsoluteOffset, new CANSparkMax(driveMotorId, MotorType.kBrushless));
    }

    /**
     * We use Rotation2d in this method to remove confusion between radians and degrees
     * @return The current angle that the pivot motor is at
     */
    protected Rotation2d getPivotAngle() {
        var absolutePosition = pivotAbsoluteEncoder.getAbsolutePosition();
        var velocity = pivotAbsoluteEncoder.getVelocity();
        var rawAngle = Rotation2d.fromRotations(StatusSignal.getLatencyCompensatedValue(absolutePosition, velocity));
        // We do this instead of plus() so it's normalized
        var normalized = MathUtil.inputModulus(rawAngle.getDegrees() + pivotAbsoluteOffset.getDegrees(), -180, 180);
        return Rotation2d.fromDegrees(normalized);
    }

    /**
     * Drive the pivot motor towards an angle
     * @param angle Angle to turn towards
     */
    private void setDesiredPivotAngle(Rotation2d angle) {
        var angleDegs = MathUtil.inputModulus(angle.getDegrees(), -180, 180);
        this.logDesiredAngle.append(angleDegs);

        var target = pivotPID.calculate(getPivotAngle().getDegrees(), angleDegs);
        pivotMotor.set(target);
    }

    public void resetPivotPID() {
        pivotPID.reset();
    }

    /**
     * Get the location of this module within the swerve drive
     * @return Location within swerve drive (units in meters)
     */
    public Translation2d getLocation() {
        return this.location;
    }

    private final static double RPM_PER_IPS = 32.73*1.03/1.022;
    private static Measure<Velocity<Angle>> convertDriveMotorSpeed(Measure<Velocity<Distance>> linearSpeed) {
        var linearSpeedIPS = linearSpeed.in(InchesPerSecond);
        var angularSpeedRPM = RPM_PER_IPS * linearSpeedIPS;
        return RPM.of(angularSpeedRPM);
    }

    /**
     * Drive the drive motor at a given speed
     * @param linearSpeed Linear speed to drive at
     */
    private void setDesiredSpeed(Measure<Velocity<Distance>> linearSpeed) {
        var targetAngularSpeed = convertDriveMotorSpeed(linearSpeed);
        drivePID.setReference(targetAngularSpeed.in(RPM), CANSparkMax.ControlType.kVelocity);
    }

    private double getDistanceTicks() {
        return driveRelativeEncoder.getPosition();
    }

    public Measure<Velocity<Angle>> getDriveAngularVelocity() {
        return RPM.of(driveRelativeEncoder.getVelocity());
    }

    public Measure<Velocity<Distance>> getDriveLinearVelocity() {
        var angularVelocity = getDriveAngularVelocity();
        var angularVelocityRPM = angularVelocity.in(RPM);
        var linearSpeedIPS = angularVelocityRPM / RPM_PER_IPS;
        return InchesPerSecond.of(linearSpeedIPS);
    }

    /**
     * Convert a number of encoder ticks to its equivalent distance in meters
     * @param ticks Number of encoder ticks
     * @return Distance (meters)
     */
    private Measure<Distance> ticksToDistance(double ticks) {
        var ticksPerInch = 6.75/12.375*1.03/1.022;
        var inches = ticks * ticksPerInch;
        return Inches.of(inches);
    }

    public Measure<Distance> getDistance() {
        var ticks = getDistanceTicks();
        return ticksToDistance(ticks);
    }

    public void setDesiredState(SwerveModuleState state) {
        var optimizedState = SwerveModuleState.optimize(state, getPivotAngle());
        setDesiredPivotAngle(optimizedState.angle);
        setDesiredSpeed(MetersPerSecond.of(optimizedState.speedMetersPerSecond));
    }

    /**
     * Get the current position of this swerve module.
     *
     * This method is useful for odometry
     * @return This module's position
     */
    public SwerveModulePosition getPosition() {
        return new SwerveModulePosition(getDistance(), getPivotAngle());
    }

    /**
     * Stop moving
     */
    public void stop() {
        this.pivotMotor.stopMotor();
        this.driveMotor.stopMotor();
    }

    public void periodic() {
        // Debug some useful values to SmartDashboard
        SmartDashboard.putNumber(name + " pivot angle", getPivotAngle().getDegrees());
        SmartDashboard.putBoolean(name + " pivot aligned", pivotPID.atSetpoint());
        SmartDashboard.putNumber(name + " drive (ticks)", getDistanceTicks());
        SmartDashboard.putNumber(name + " drive (meters)", getDistance().in(Meters));
        SmartDashboard.putNumber(name + " drive velocity (RPM)", getDriveAngularVelocity().in(RPM));
    }
}
