"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Modal from "@/refresh-components/Modal";
import Button from "@/refresh-components/buttons/Button";
import Text from "@/refresh-components/texts/Text";
import { Checkbox } from "@opal/components";

const OUTPUT_SIZE = 256;
const MIN_ZOOM = 1;
const MAX_ZOOM = 3;
const ZOOM_STEP = 0.05;
const CROP_AREA_SIZE = 220;

interface LogoCropModalProps {
  imageFile: File;
  onCrop: (blob: Blob) => void;
  onCancel: () => void;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

export default function LogoCropModal({
  imageFile,
  onCrop,
  onCancel,
}: LogoCropModalProps) {
  const [imageSrc, setImageSrc] = useState("");
  const [imageLoaded, setImageLoaded] = useState(false);
  const [zoom, setZoom] = useState(MIN_ZOOM);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [transparent, setTransparent] = useState(false);

  const imageRef = useRef<HTMLImageElement>(null);
  const cropRef = useRef<HTMLDivElement>(null);

  // Load image from File
  useEffect(() => {
    const url = URL.createObjectURL(imageFile);
    setImageSrc(url);
    return () => URL.revokeObjectURL(url);
  }, [imageFile]);

  // Reset offset when zoom changes
  const maxOffset = (CROP_AREA_SIZE * (zoom - 1)) / 2;

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      setIsDragging(true);
      setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
    },
    [offset]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isDragging) return;
      setOffset({
        x: clamp(e.clientX - dragStart.x, -maxOffset, maxOffset),
        y: clamp(e.clientY - dragStart.y, -maxOffset, maxOffset),
      });
    },
    [isDragging, dragStart, maxOffset]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      const touch = e.touches[0];
      if (!touch) return;
      setIsDragging(true);
      setDragStart({ x: touch.clientX - offset.x, y: touch.clientY - offset.y });
    },
    [offset]
  );

  const handleTouchMove = useCallback(
    (e: React.TouchEvent) => {
      if (!isDragging) return;
      const touch = e.touches[0];
      if (!touch) return;
      setOffset({
        x: clamp(touch.clientX - dragStart.x, -maxOffset, maxOffset),
        y: clamp(touch.clientY - dragStart.y, -maxOffset, maxOffset),
      });
    },
    [isDragging, dragStart, maxOffset]
  );

  const handleTouchEnd = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleZoomChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const newZoom = parseFloat(e.target.value);
      setZoom(newZoom);
      // Clamp offset to new max
      const newMaxOffset = (CROP_AREA_SIZE * (newZoom - 1)) / 2;
      setOffset((prev) => ({
        x: clamp(prev.x, -newMaxOffset, newMaxOffset),
        y: clamp(prev.y, -newMaxOffset, newMaxOffset),
      }));
    },
    []
  );

  const cropAndExport = useCallback(() => {
    const img = imageRef.current;
    if (!img) return;

    const canvas = document.createElement("canvas");
    canvas.width = OUTPUT_SIZE;
    canvas.height = OUTPUT_SIZE;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    if (!transparent) {
      ctx.fillStyle = "#FFFFFF";
      ctx.fillRect(0, 0, OUTPUT_SIZE, OUTPUT_SIZE);
    }

    // Calculate source crop rectangle
    const imgW = img.naturalWidth;
    const imgH = img.naturalHeight;
    const fitScale = Math.max(imgW, imgH) / CROP_AREA_SIZE;
    const cropSize = (CROP_AREA_SIZE / zoom) * fitScale;

    const centerX = imgW / 2;
    const centerY = imgH / 2;
    const offsetScale = fitScale / zoom;

    const sx = centerX - cropSize / 2 - offset.x * offsetScale;
    const sy = centerY - cropSize / 2 - offset.y * offsetScale;

    ctx.drawImage(img, sx, sy, cropSize, cropSize, 0, 0, OUTPUT_SIZE, OUTPUT_SIZE);

    canvas.toBlob(
      (blob) => {
        if (blob) onCrop(blob);
      },
      "image/png",
      1.0
    );
  }, [zoom, offset, transparent, onCrop]);

  // Render preview at a given size
  const renderPreview = (size: number, label: string) => {
    const img = imageRef.current;
    if (!img || !imageLoaded) {
      return (
        <div className="flex flex-col items-center gap-1">
          <div
            className="rounded-full bg-background-neutral-03"
            style={{ width: size, height: size }}
          />
          <Text text03 secondaryBody>
            {label}
          </Text>
        </div>
      );
    }

    const imgW = img.naturalWidth;
    const imgH = img.naturalHeight;
    const fitScale = Math.max(imgW, imgH) / CROP_AREA_SIZE;
    const previewScale = size / OUTPUT_SIZE;
    const cropSize = (CROP_AREA_SIZE / zoom) * fitScale;
    const offsetScale = fitScale / zoom;

    const sx = imgW / 2 - cropSize / 2 - offset.x * offsetScale;
    const sy = imgH / 2 - cropSize / 2 - offset.y * offsetScale;

    return (
      <div className="flex flex-col items-center gap-1">
        <div
          className="rounded-full overflow-hidden relative"
          style={{
            width: size,
            height: size,
            background: transparent ? "repeating-conic-gradient(#e5e5e5 0% 25%, #fff 0% 50%) 50%/8px 8px" : "#fff",
          }}
        >
          <canvas
            width={size}
            height={size}
            ref={(el) => {
              if (!el) return;
              const ctx = el.getContext("2d");
              if (!ctx) return;
              ctx.clearRect(0, 0, size, size);
              if (!transparent) {
                ctx.fillStyle = "#FFFFFF";
                ctx.fillRect(0, 0, size, size);
              }
              ctx.drawImage(
                img,
                sx,
                sy,
                cropSize,
                cropSize,
                0,
                0,
                size,
                size
              );
            }}
          />
        </div>
        <Text text03 secondaryBody>
          {label}
        </Text>
      </div>
    );
  };

  // Image transform style for crop area
  const imgW = imageRef.current?.naturalWidth ?? 1;
  const imgH = imageRef.current?.naturalHeight ?? 1;
  const fitScale = CROP_AREA_SIZE / Math.max(imgW, imgH);

  return (
    <Modal open onOpenChange={() => onCancel()}>
      <Modal.Content width="sm" height="fit">
        <Modal.Header title="Logo zuschneiden" onClose={onCancel} />
        <Modal.Body>
          <div className="flex flex-col items-center gap-4">
            {/* Hidden image for natural dimensions */}
            <img
              ref={imageRef}
              src={imageSrc}
              alt=""
              className="hidden"
              onLoad={() => setImageLoaded(true)}
            />

            {/* Crop area */}
            <div
              ref={cropRef}
              className="relative overflow-hidden rounded-08 cursor-grab active:cursor-grabbing select-none"
              style={{
                width: CROP_AREA_SIZE,
                height: CROP_AREA_SIZE,
                background: transparent
                  ? "repeating-conic-gradient(#e5e5e5 0% 25%, #fff 0% 50%) 50%/16px 16px"
                  : "#f5f5f5",
              }}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              onTouchStart={handleTouchStart}
              onTouchMove={handleTouchMove}
              onTouchEnd={handleTouchEnd}
            >
              {imageLoaded && (
                <img
                  src={imageSrc}
                  alt="Crop preview"
                  draggable={false}
                  style={{
                    position: "absolute",
                    left: "50%",
                    top: "50%",
                    width: imgW * fitScale * zoom,
                    height: imgH * fitScale * zoom,
                    transform: `translate(calc(-50% + ${offset.x}px), calc(-50% + ${offset.y}px))`,
                    pointerEvents: "none",
                  }}
                />
              )}
            </div>

            {/* Zoom slider */}
            <div className="w-full flex items-center gap-3">
              <Text text03 secondaryBody>
                Zoom
              </Text>
              <input
                type="range"
                min={MIN_ZOOM}
                max={MAX_ZOOM}
                step={ZOOM_STEP}
                value={zoom}
                onChange={handleZoomChange}
                className="flex-1 accent-action-link-05"
              />
              <Text text03 secondaryBody className="w-10 text-right">
                {zoom.toFixed(1)}x
              </Text>
            </div>

            {/* Transparent background toggle */}
            <div className="w-full flex items-center gap-2">
              <Checkbox
                checked={transparent}
                onCheckedChange={(checked) => setTransparent(checked)}
                aria-label="Transparenter Hintergrund"
              />
              <Text text03>Transparenter Hintergrund</Text>
            </div>

            {/* Previews */}
            <div className="w-full">
              <Text text03 secondaryBody className="pb-2">
                Vorschau
              </Text>
              <div className="flex items-end gap-6 justify-center">
                {renderPreview(24, "Sidebar")}
                {renderPreview(44, "Login")}
                {renderPreview(32, "Favicon")}
              </div>
            </div>
          </div>
        </Modal.Body>
        <Modal.Footer>
          <Button secondary onClick={onCancel}>
            Abbrechen
          </Button>
          <Button main primary onClick={cropAndExport}>
            Übernehmen
          </Button>
        </Modal.Footer>
      </Modal.Content>
    </Modal>
  );
}
