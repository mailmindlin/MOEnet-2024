package frc.robot.subsystems;

import edu.wpi.first.math.MathUtil;
import edu.wpi.first.math.geometry.Pose2d;
import edu.wpi.first.math.geometry.Rotation2d;
import edu.wpi.first.math.geometry.Translation2d;
import edu.wpi.first.math.kinematics.ChassisSpeeds;
import edu.wpi.first.math.kinematics.SwerveDriveKinematics;
import edu.wpi.first.math.kinematics.SwerveDriveOdometry;
import edu.wpi.first.math.kinematics.SwerveDriveWheelPositions;
import edu.wpi.first.math.kinematics.SwerveModulePosition;
import edu.wpi.first.util.datalog.StructLogEntry;
import edu.wpi.first.wpilibj.DataLogManager;
import edu.wpi.first.wpilibj2.command.SubsystemBase;
import frc.robot.sensor.imu.Gyro3d;

public class SwerveDrive extends SubsystemBase {
    private Gyro3d gyro;
    private Rotation2d gyroOffset = new Rotation2d();

    private final StructLogEntry<Pose2d> logOdometry;

    private final SwerveModule[] swerveModules;
    private final SwerveDriveKinematics kinematics;
    private final SwerveDriveOdometry odometry;

    public SwerveDrive(Gyro3d gyro, SwerveModule... modules) {
        this.gyro = gyro;
        this.swerveModules = modules;

        var log = DataLogManager.getLog();
        this.logOdometry = StructLogEntry.create(log, "swerve/odom", Pose2d.struct);

        var offsets = new Translation2d[modules.length];
        for (int i = 0; i < modules.length; i++)
            offsets[i] = modules[i].getLocation();
        this.kinematics = new SwerveDriveKinematics(offsets);
        this.odometry = new SwerveDriveOdometry(kinematics, gyro.getRotation2d(), getPositions().positions);
    }

    // ========== Driving ==========

    /**
     * Drive relative to the field
     * @param fieldRelativeSpeeds Field-relative speeds to drive at
     */
    public void driveFieldRelative(ChassisSpeeds fieldRelativeSpeeds) {
        var robotAngle = getRobotAngle();
        var robotRelativeSpeeds = ChassisSpeeds.fromFieldRelativeSpeeds(fieldRelativeSpeeds, robotAngle);

        driveRobotRelative(robotRelativeSpeeds);
    }

    /**
     * Drive relative to the robot.
     * @param speeds Robot-relative speeds to drive at
     */
    public void driveRobotRelative(ChassisSpeeds speeds) {
        var states = kinematics.toSwerveModuleStates(speeds);
        for (int i = 0; i < swerveModules.length; i++) {
            var swerveModule = swerveModules[i];
            var state = states[i];

            swerveModule.setDesiredState(state);
        }
    }

    /**
     * Stop all motor movement
     */
    public void stop() {
        // Stop all modules
        for (SwerveModule module : this.swerveModules)
            module.stop();
    }

    // ========== Gyro ==========

    /**
     * Get angle relative to the field
     * @return Angle relative to the field
     * @see #resetRobotAngle()
     */
    public Rotation2d getRobotAngle() {
        var rawAngle = gyro.getRotation2d();
        var offsetAngle = rawAngle.minus(gyroOffset);
        // Normalize between -180 and 180
        return Rotation2d.fromRadians(MathUtil.angleModulus(offsetAngle.getRadians()));
    }

    /**
     * Reset the angle of field-to-robot to 0\deg
     * @see #resetRobotAngle(Rotation2d)
     */
    public void resetRobotAngle() {
        resetRobotAngle(new Rotation2d(0));
    }

    public void resetRobotAngle(Rotation2d currentAngle) {
        var gyroCurrent = gyro.getRotation2d();
        this.gyroOffset = gyroCurrent.minus(currentAngle);
    }

    // ========== Odometry ==========

    /**
     * Get the positions of each swerve module
     * @return Positions of each swerve module
     */
    protected SwerveDriveWheelPositions getPositions() {
        var positions = new SwerveModulePosition[swerveModules.length];
        for (int i = 0; i < swerveModules.length; i++)
            positions[i] = swerveModules[i].getPosition();
        return new SwerveDriveWheelPositions(positions);
    }

    /**
     * Reset odometry back to (0, 0)
     * @see #resetPosition(Pose2d) 
     */
    public void resetPosition() {
        resetPosition(new Pose2d());
    }

    public void resetPosition(Pose2d currentPose) {
        this.resetRobotAngle(currentPose.getRotation());
        this.odometry.resetPosition(gyro.getRotation2d(), getPositions(), currentPose);
    }

    public SwerveModule getModuleIndex(int idx) {
        return this.swerveModules[idx];
    }

    @Override
    public void periodic() {
        // Update each of the modules
        for (SwerveModule module : swerveModules)
            module.periodic();
        
        var odomPose = this.odometry.update(gyro.getRotation2d(), getPositions());
        this.logOdometry.append(odomPose);
    }
}
