from rest_framework import serializers


class UsedStatSerializer(serializers.Serializer):
    used_storage = serializers.IntegerField()
    used_ram = serializers.IntegerField()
    used_cpu = serializers.IntegerField()
    used_net_tx = serializers.IntegerField()
    used_net_rx = serializers.IntegerField()

    chart = serializers.DictField()
