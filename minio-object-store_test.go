package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"testing"

	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
)

func TestCreateBucket(t *testing.T) {
	// Initializing minio client

	ctx := context.Background()
	endpoint := os.Getenv("MINIO_ENDPOINT")
	accessKey := os.Getenv("MINIO_ACCESS_KEY")
	secretKey := os.Getenv("MINIO_SECRET_KEY")
	useSSL := false

	minioClient, err := minio.New(endpoint, &minio.Options{
		Creds:  credentials.NewStaticV4(accessKey, secretKey, ""),
		Secure: useSSL,
	})
	if err != nil {
		t.Errorf("Failed to initialize minioClient")
	}

	// creating a bucket
	bucketName := "images"

	err = minioClient.MakeBucket(ctx, bucketName, minio.MakeBucketOptions{})
	if err != nil {
		// check for exist
		exists, errBucketExist := minioClient.BucketExists(ctx, bucketName)
		if errBucketExist == nil && exists {
			log.Printf("already own %s", bucketName)
		} else {
			t.Errorf("Failed to create bucket")
		}
	} else {
		log.Printf("successfully created bucket %s", bucketName)
	}

	buckets, err := minioClient.ListBuckets(ctx)
	if err != nil {
		t.Errorf("Failed to list buckets")

	}
	for _, bucket := range buckets {
		fmt.Println(bucket)
	}

	// uploading a file
	objectName := "myObject"
	file, err := os.Open("/app/minio-object-store_test.go")
	if err != nil {
		t.Log(err)

	}
	defer file.Close()

	fileStat, err := file.Stat()
	if err != nil {
		t.Log(err)

	}
	uploadInfo, err := minioClient.PutObject(ctx, bucketName, objectName, file, fileStat.Size(), minio.PutObjectOptions{})
	if err != nil {
		t.Errorf("Failed to upload file")

	} else {
		fmt.Println("successfully uploaded file", uploadInfo)
	}

	ctx, cancel := context.WithCancel(ctx)
	defer cancel()

	objectCh := minioClient.ListObjects(ctx, bucketName, minio.ListObjectsOptions{})
	for object := range objectCh {
		if object.Err != nil {
			fmt.Println(object.Err)

		}
		fmt.Println(object)
	}

	// Removing the file
	opts := minio.RemoveObjectOptions{}
	err = minioClient.RemoveObject(ctx, bucketName, objectName, opts)
	if err != nil {
		fmt.Println(err)

	} else {
		fmt.Printf("successfully removed the object %s   |", objectName)
	}

	//Removing the bucket
	err = minioClient.RemoveBucket(ctx, bucketName)
	if err != nil {
		fmt.Println(err)
		return
	} else {
		fmt.Printf("Successfully removed bucket %s", bucketName)
	}
}
