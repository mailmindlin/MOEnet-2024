package frc.robot.sensor.vision.io;

import java.nio.ByteBuffer;

import edu.wpi.first.math.MatBuilder;
import edu.wpi.first.math.Matrix;
import edu.wpi.first.math.Nat;
import edu.wpi.first.math.numbers.N6;
import edu.wpi.first.util.struct.Struct;

public class Mat66Struct implements Struct<Matrix<N6, N6>> {
    public static final Mat66Struct struct = new Mat66Struct();

    private transient String schemaCache;

    @Override
    @SuppressWarnings("unchecked")
    public Class<Matrix<N6, N6>> getTypeClass() {
        return (Class<Matrix<N6, N6>>) (Class<?>) Matrix.class;
    }

    @Override
    public String getTypeString() {
        return "struct:Mat66";
    }

    @Override
    public int getSize() {
        return Double.BYTES * 36;
    }

    @Override
    public String getSchema() {
        if (this.schemaCache != null)
            return this.schemaCache;
        var builder = new StringBuilder();
        for (int i = 0; i < 35; i++)
            builder.append("double m" + i + ";");
        builder.append("double m36");
        return this.schemaCache = builder.toString();
    }

    @Override
    public Matrix<N6, N6> unpack(ByteBuffer bb) {
        var arr = new double[36];
        bb.asDoubleBuffer().get(arr);
        bb.position(bb.position() + getSize());
        return MatBuilder.fill(Nat.N6(), Nat.N6(), arr);
    }

    @Override
    public void pack(ByteBuffer bb, Matrix<N6, N6> value) {
        var arr = value.getData();
        bb.asDoubleBuffer().put(arr);
        bb.position(bb.position() + getSize());
    }
}
