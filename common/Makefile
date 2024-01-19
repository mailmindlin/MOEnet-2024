sources = moenet.proto
all: server client

server:
	protoc -I . --python_out=../server/typedef/net moenet.proto

client:
	# mkdir ../MOEnet-client/src/main/java/frc/robot/sensor/vision/net
	# protoc -I . --java_out=../MOEnet-client/src/main/java moenet.proto
	cp ./moenet.proto ../MOEnet-client/src/main/proto/.