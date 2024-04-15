package frc.robot.sensor.vision;

import java.util.Objects;
import java.util.List;

import edu.wpi.first.apriltag.AprilTagFieldLayout;
import edu.wpi.first.apriltag.AprilTagFields;
import edu.wpi.first.math.geometry.Pose2d;
import edu.wpi.first.math.geometry.Pose3d;
import edu.wpi.first.math.geometry.Transform3d;
import edu.wpi.first.math.geometry.proto.Pose3dProto;
import edu.wpi.first.math.kinematics.Kinematics;
import edu.wpi.first.math.kinematics.Odometry;
import edu.wpi.first.networktables.NetworkTableInstance;
import edu.wpi.first.wpilibj2.command.CommandScheduler;
import frc.robot.sensor.vision.moenet.MoeNet;
import frc.robot.sensor.vision.io.ObjectDetection;

public class Vision implements PoseSensor {
	public static Builder builder() {
		return new Builder();
	}

	public static class Builder {
		private NetworkTableInstance nt = NetworkTableInstance.getDefault();
		private AprilTagFieldLayout apriltags;
		private Odometry<?> odometry;

		public Builder setNetworkTables(NetworkTableInstance nt) {
			return this;
		}
		public Builder setAprilTags(AprilTagFields field) {
			Objects.requireNonNull(field, "AprilTag field");
			return setAprilTags(field.loadAprilTagLayoutField());
		}
		public Builder setAprilTags(AprilTagFieldLayout apriltags) {
			return this;
		}

		public Builder addMoenet() {
			return addMoenet(MoeNet.DEFAULT_NAME);
		}
		public Builder addMoenet(String name) {
			return this;
		}

		public Builder addCamera(VisionSystem vision) {
			Objects.requireNonNull(vision);
			return this;
		}

		public <S, P> Builder addOdometry(Kinematics<S, P> kinematics) {
			return this;
		}

		public Vision build() {
			return new Vision();
		}
	}

	private Pose3d fieldToRobot = new Pose3d();
	private Transform3d odomToRobot = new Transform3d();
	private List<ObjectDetection> objects = new ArrayList<>();
	private MoeNet moenet;

	private Vision() {

	}

	/**
	 * Tell the vision system that we know where we are
	 * @param pose
	 */
	public void setPose(Pose3d pose) {
		//TODO
	}

	public Transform3d getOdometryCorrection() {
		return null;
	}

	/**
	 * Periodic update.
	 * This should be called AFTER the odometry is refreshed.
	 */
	public void periodic() {

	}

	@Override
	public Pose3d getPose3d() {
		// TODO Auto-generated method stub
		throw new UnsupportedOperationException("Unimplemented method 'getPose3d'");
	}

	@Override
	public Pose2d getPose2d() {
		// TODO Auto-generated method stub
		throw new UnsupportedOperationException("Unimplemented method 'getPose2d'");
	}

	@Override
	public boolean isRelative() {
		// TODO Auto-generated method stub
		throw new UnsupportedOperationException("Unimplemented method 'isRelative'");
	}
}
