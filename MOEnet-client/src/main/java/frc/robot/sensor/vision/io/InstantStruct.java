package frc.robot.sensor.vision.io;

import java.nio.ByteBuffer;
import java.time.Instant;

import edu.wpi.first.util.struct.Struct;

public class InstantStruct implements Struct<Instant> {
    public static final InstantStruct struct = new InstantStruct();
    
    @Override
    public int getSize() {
        return Long.BYTES + Integer.BYTES;
    }

    @Override
    public String getSchema() {
        return "long s;int ns";
    }

    @Override
    public Instant unpack(ByteBuffer bb) {
        var s = bb.getLong();
        var ns = bb.getInt();
        return Instant.ofEpochSecond(s, ns);
    }

    @Override
    public void pack(ByteBuffer bb, Instant value) {
        bb.putLong(value.getEpochSecond());
        bb.putInt(value.getNano());
    }

    @Override
    public Class<Instant> getTypeClass() {
        return Instant.class;
    }

    @Override
    public String getTypeString() {
        return "struct Instant";
    }
}
