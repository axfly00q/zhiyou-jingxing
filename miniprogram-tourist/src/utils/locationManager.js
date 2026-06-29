/**
 * Location Manager
 * 处理强/弱 GPS 状态切换及 iBeacon 兜底方案
 */
class LocationManager {
  constructor() {
    this.isListening = false;
    this.isWeakGPS = false;
    this.currentLocation = null;
    this.callbacks = [];
    this.beaconActive = false;
    this._handleLocationChange = null;
    this._boundBeaconUpdate = this._handleBeaconUpdate.bind(this);

    // 假设这是已知信标对应的经纬度映射表
    this.beaconMap = {
      'FDA50693-A4E2-4FB1-AFCF-C6EB07647825_10001_12345': {
        latitude: 31.3262,
        longitude: 120.6279,
        name: '远香堂'
      }
    };
  }

  // 暴露给页面的监听方法
  onLocationUpdate(callback) {
    this.callbacks.push(callback);
    return () => {
      this.callbacks = this.callbacks.filter(cb => cb !== callback);
    };
  }

  // 内部触发更新
  _triggerUpdate(locationData) {
    this.currentLocation = locationData;
    this.callbacks.forEach(cb => {
      try {
        cb(locationData);
      } catch (err) {
        console.error('location callback fail', err);
      }
    });
  }

  start() {
    if (this.isListening) return;

    // 1. 获取基础授权
    uni.authorize({
      scope: 'scope.userLocation',
      success: () => {
        // 2. 开启后台/前台定位更新
        uni.startLocationUpdate({
          success: () => {
            this.isListening = true;
            this.listenGPS();
          },
          fail: (err) => {
            console.error('startLocationUpdate fail', err);
          }
        });
      },
      fail: () => {
        uni.showModal({
          title: '需要定位权限',
          content: '导览服务需要您的位置信息',
          showCancel: false
        });
      }
    });
  }

  stop() {
    if (this.isListening) {
      uni.stopLocationUpdate();
      uni.offLocationChange(this._handleLocationChange);
      this.isListening = false;
    }
    if (this.beaconActive) {
      this._stopBeacon();
    }
  }

  listenGPS() {
    if (this._handleLocationChange) {
      uni.offLocationChange(this._handleLocationChange);
    }
    this._handleLocationChange = (res) => {
      // res: { latitude, longitude, accuracy, speed, etc. }
      
      const systemInfo = uni.getSystemInfoSync();
      const isDevTools = systemInfo.platform === 'devtools';

      // 判断是否弱 GPS（例如精度 > 50米 或 无法获取精度时默认为弱。开发者工具下不启用该限制）
      if (res.accuracy && res.accuracy > 50 && !isDevTools) {
        if (!this.isWeakGPS) {
          console.warn('进入弱 GPS 状态，尝试开启 iBeacon 兜底');
          this.isWeakGPS = true;
          this._startBeacon();
        }
        // 即使在弱 GPS 状态下，在没有获取到更精确的 iBeacon 定位前，也使用当前 coordinates 进行低精度更新，保障画面流畅且不卡死
        this._triggerUpdate({
          latitude: res.latitude,
          longitude: res.longitude,
          type: '弱 GPS'
        });
      } else {
        if (this.isWeakGPS) {
          console.log('GPS 信号恢复，关闭 iBeacon兜底');
          this.isWeakGPS = false;
          this._stopBeacon();
        }
        // 强 GPS 状态直接更新
        this._triggerUpdate({
          latitude: res.latitude,
          longitude: res.longitude,
          type: isDevTools ? 'GPS(仿真)' : 'GPS'
        });
      }
    };

    uni.onLocationChange(this._handleLocationChange);
  }

  _startBeacon() {
    if (this.beaconActive) return;
    
    // 初始化蓝牙
    uni.openBluetoothAdapter({
      success: () => {
        uni.startBeaconDiscovery({
          uuids: ['FDA50693-A4E2-4FB1-AFCF-C6EB07647825'], // 景区的 UUID
          success: () => {
            this.beaconActive = true;
            uni.onBeaconUpdate(this._boundBeaconUpdate);
          },
          fail: (err) => {
            console.error('信标扫描启动失败', err);
            // 可以在此处弹出让用户扫码定位的提示 (方案 B)
          }
        });
      },
      fail: (err) => {
        console.error('蓝牙未开启', err);
        uni.showToast({ title: '请开启蓝牙以提高定位精度', icon: 'none' });
      }
    });
  }

  _stopBeacon() {
    if (!this.beaconActive) return;
    if (typeof uni.offBeaconUpdate === 'function') {
      uni.offBeaconUpdate(this._boundBeaconUpdate);
    }
    uni.stopBeaconDiscovery();
    uni.closeBluetoothAdapter();
    this.beaconActive = false;
  }

  _handleBeaconUpdate(res) {
    if (!this.isWeakGPS) return; // 如果已经切回强 GPS，忽略信标

    const beacons = res.beacons;
    if (beacons && beacons.length > 0) {
      // 找出距离最近的信标
      const closest = beacons.reduce((prev, curr) => (prev.distance < curr.distance) ? prev : curr);
      
      const beaconKey = `${closest.uuid}_${closest.major}_${closest.minor}`.toUpperCase();
      const mappedLocation = this.beaconMap[beaconKey];

      if (mappedLocation) {
        // 使用信标坐标兜底
        this._triggerUpdate({
          latitude: mappedLocation.latitude,
          longitude: mappedLocation.longitude,
          type: 'iBeacon',
          name: mappedLocation.name
        });
      }
    }
  }
}

export default new LocationManager();
